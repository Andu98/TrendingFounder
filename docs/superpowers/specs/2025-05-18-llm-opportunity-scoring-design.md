# LLM-Based Romanian Market Opportunity Scoring: Design Document

**Date**: 2025-05-18  
**Status**: Draft for Review  
**Related Spec**: `docs/Update_scoring.md`

---

## 1. Overview

### Goal
Replace the deterministic scoring pipeline with an **LLM-first** system that evaluates whether a trending domain represents a realistic and interesting opportunity to adapt, clone, localize, or build for the Romanian market.

### Key Principle
The LLM is the **main evaluator**. Deterministic logic is used only for:
- Collecting cheap signals (trend data, observations)
- Pre-filtering obvious junk
- Passing context to the LLM
- Fallback scoring if LLM fails
- Hard penalties for known global giants (cap at 20)

### Separated Concerns
The scoring command runs **independently** from the daily Cloudflare crawl. It evaluates:
- New domains discovered in future crawls
- Existing domains already in Supabase

---

## 2. System Architecture

```
┌──────────────────────────────────────────────────────────────┐
│                    update-opportunity-scores                  │
│                   (standalone command)                       │
├──────────────────────────────────────────────────────────────┤
│ 1. Load domains from Supabase (with filters)                 │
│ 2. Gather observations → compute trend_score                 │
│ 3. Optional: fetch homepage excerpt (--fetch-homepage)      │
│ 4. Build prompt with all context                             │
│ 5. Call LLM via LMStudioClient (low temp: 0–0.1)            │
│ 6. Validate JSON against strict schema                       │
│ 7. Apply guardrails: global giant cap                        │
│ 8. Save results to domains table                             │
│ 9. Continue on errors; log failures                          │
└──────────────────────────────────────────────────────────────┘
```

### Data Flow

1. **Input**: Domain record + recent observations + optional homepage excerpt
2. **LLM Output**: Strict JSON with dimensions, scores, and explanations
3. **Persisted Fields**: See Section 4 below
4. **Dashboard**: Reads from `domains` table via existing views (updated to include new fields)

---

## 3. Database Schema Changes

### 3.1 Migration: `supabase/schemas/004_opportunity_scores.sql`

Add columns directly to `domains` table (simplest, matches existing LLM enrichment pattern):

```sql
ALTER TABLE domains
    ADD COLUMN opportunity_score NUMERIC,
    ADD COLUMN opportunity_breakdown JSONB,
    ADD COLUMN opportunity_summary TEXT,
    ADD COLUMN opportunity_idea TEXT,
    ADD COLUMN opportunity_category TEXT,
    ADD COLUMN opportunity_type TEXT,
    ADD COLUMN opportunity_confidence INTEGER,
    ADD COLUMN trend_score NUMERIC,
    ADD COLUMN llm_opportunity_model TEXT,
    ADD COLUMN llm_opportunity_prompt_version TEXT,
    ADD COLUMN llm_opportunity_updated_at TIMESTAMPTZ;
```

**Rationale**:
- No need for a separate history table; overwrite on re‑score is acceptable per spec.
- Separate columns for `opportunity_category` and `opportunity_type` simplify filtering and indexing.
- `opportunity_breakdown` stores the complete LLM JSON response for inspection and future analysis.
- `trend_score` is a snapshot of the domain's current raw momentum.

### 3.2 Views Update

Update `supabase/schemas/002_views.sql` to include opportunity fields in:

- `v_domains_today`
- `v_domains_this_week`
- `get_domains_for_range()` RPC function

Add to SELECT lists and GROUP BY as needed. Example addition to `v_domains_today`:

```sql
SELECT
    dom.id,
    dom.normalized_domain,
    dom.display_url,
    dom.first_seen_date,
    dom.llm_summary,
    dom.llm_category,
    dom.llm_business_model,
    dom.review_status,
    dom.initial_score,
    dom.latest_best_score,
    dom.opportunity_score,
    dom.opportunity_category,
    dom.opportunity_type,
    dom.opportunity_confidence,
    dom.trend_score,
    MAX(obs.observation_score) AS best_score_today,
    ...
```

Similarly update `get_domains_for_range` to surface these fields with appropriate ordering defaults.

---

## 4. Python Modules (New Package: `src/opportunity/`)

### 4.1 `prompt.py`

Function: `build_opportunity_prompt(
    domain: str,
    display_url: str,
    trend_score: float,
    countries_observed: list[str],
    ranking_types: list[str],
    best_rank: int,
    pct_rank_change: float | None,
    first_seen_at: str,
    existing_category: str | None,
    existing_summary: str | None,
    existing_llm_potential: int | None,
    review_status: str,
    romanian_signals: bool,
    homepage_excerpt: str | None
) -> str`

**Prompt**: Exactly as specified in `Update_scoring.md` – Romanian market analyst, strict JSON, scoring guidance 0–100, reward local tools, penalize global giants. See spec lines 297–382.

### 4.2 `schemas.py`

Pydantic model for the strict JSON schema:

```python
class OpportunityScoreResult(BaseModel):
    opportunity_score: int = Field(..., ge=0, le=100)
    confidence: int = Field(..., ge=0, le=100)
    is_global_giant: bool
    is_too_generic: bool
    romania_market_fit: int = Field(..., ge=1, le=5)
    local_gap: int = Field(..., ge=1, le=5)
    buildability: int = Field(..., ge=1, le=5)
    monetization_clarity: int = Field(..., ge=1, le=5)
    novelty: int = Field(..., ge=1, le=5)
    trend_relevance: int = Field(..., ge=1, le=5)
    competition_saturation: int = Field(..., ge=1, le=5)
    complexity: int = Field(..., ge=1, le=5)
    regulatory_risk: int = Field(..., ge=1, le=5)
    recommended_category: str
    opportunity_type: str = Field(..., pattern=r"^(local_marketplace|b2b_saas|consumer_app|vertical_saas|content_platform|ecommerce_tool|education_tool|healthcare_tool|logistics_tool)$")
    one_sentence_summary: str = Field(..., max_length=200)
    romania_adaptation_idea: str = Field(..., max_length=500)
    why_it_scores_this_way: str = Field(..., max_length=500)
    red_flags: list[str] = Field(default_factory=list)
    suggested_mvp: str = Field(..., max_length=500)
```

### 4.3 `scorer.py`

Class `OpportunityScorer`:

- `__init__(base_url: str | None, model: str | None, timeout: float)`
- `score_domain(context: dict, homepage_excerpt: str | None) -> OpportunityScoreResult`
- **Internals**:
  - Reuse `httpx` async client from existing `LMStudioClient` pattern.
  - Use `temperature=0` or `0.1`.
  - Build payload with JSON schema for strict output.
  - Retry (4 attempts, exponential backoff) on network errors, invalid JSON, validation errors.
  - Return error wrapper on failure; do **not** raise (calling command handles persistence).

**Guardrail Application**:
Will be applied in the command layer, not the scorer, because it depends on domain metadata (known giant list).

### 4.4 `constants.py`

Known global giants list (expanded from spec and existing `KNOWN_GIANTS`):

```python
KNOWN_GLOBAL_GIANTS = frozenset({
    "amazon.com", "udemy.com", "box.com", "google.com", "youtube.com",
    "facebook.com", "instagram.com", "netflix.com", "booking.com", "airbnb.com",
    "microsoft.com", "apple.com", "temu.com", "aliexpress.com", "wikipedia.org",
    "linkedin.com", "x.com", "twitter.com", "tiktok.com", "microsoft.com",
    "github.com", "stackoverflow.com", "zoom.us", "slack.com", "whatsapp.com",
    "reddit.com", "pinterest.com", "spotify.com", "twitch.tv", "discord.com",
    "notion.so", "canva.com", "figma.com", "adobe.com", "salesforce.com",
    "oracle.com", "ibm.com", "intel.com", "nvidia.com", "tesla.com",
})
```

Cap: `final_score = min(llm_score, 20)` for known giants unless LLM gives strong reason? We'll simply cap at 20 for simplicity as spec suggests.

---

## 5. Main Command: `update-opportunity-scores`

**Entry Point**: `main.py` at project root:

```python
# main.py
import sys
from pathlib import Path

def main():
    args = sys.argv[1:]
    if not args or args[0] != "update-opportunity-scores":
        print("Usage: python main.py update-opportunity-scores [options]")
        return 2
    # Import and run command
    from src.opportunity.update_opportunity_scores import cli
    return cli()

if __name__ == "__main__":
    raise SystemExit(main())
```

The actual implementation resides in `src/opportunity/update_opportunity_scores.py`.

### CLI Arguments (argparse)

- `--only-missing` → score only where `opportunity_score IS NULL`
- `--limit N` → max domains to process
- `--min-trend-score N` → filter: `trend_score >= N`
- `--dry-run` → print without saving; also skip homepage fetching
- `--force` → re‑score even if already present
- `--fetch-homepage` → enable homepage fetching with BeautifulSoup

Optional: `--concurrency N` for parallel LLM calls (default: 5). Use async semaphore.

### Command Steps

1. **Build query** against `domains` table using filters:
   - Base: select all columns needed (list them).
   - If `--only-missing`: add `WHERE opportunity_score IS NULL`
   - If `--force`: ignore existing scores
   - We cannot filter by `trend_score` directly in the query because it's computed from observations (unless we add a subquery/join). Simpler: fetch all candidate domains, then compute trend_score in Python and apply `--min-trend-score` client‑side.
   - Apply `--limit` after filters.

2. **Fetch observations** per domain: query `domain_observations` for recent data (e.g., last 7 days) to compute:
   - `trend_score`: max of `observation_score` (use the scoring formula on the fly if needed) – but careful: `observation_score` is already computed and stored. However, it may change over time if we rescore old observations? Observations are static; their scores are based on rank etc. at that time. The spec says `trend_score` is "based on the existing Cloudflare scoring logic." So we can simply take the **maximum** `observation_score` among the domain's recent observations (last 7 days). That's consistent with how the dashboard computes `best_score_today`/`week`. We'll compute it from observations we fetch.
   - `countries_observed`: distinct `country_code`
   - `ranking_types`: distinct `ranking_type`
   - `best_rank`: minimum rank across observations
   - `pct_rank_change`: maybe latest or max? The prompt expects a value; we'll use the maximum pct_rank_change observed.
   - `romanian_signals`: `True` if any `country_code = 'RO'` in any observation.

3. **Optional homepage fetch**: If `--fetch-homepage` and not dry‑run:
   - Use `httpx.AsyncClient` with timeout=5.0, `follow_redirects=True`, and `limits(max_response_body_length=500*1024)`.
   - Parse with `BeautifulSoup(html, "html.parser")`.
   - Extract:
     - `title`: `<title>` text.
     - `meta description`: `<meta name="description">` content.
     - `headings`: `<h1>` and `<h2>` texts (joined).
     - `first text block`: first `<p>` or div with meaningful text length > 20 chars.
   - Build a short excerpt: `f"Title: {title}\nDescription: {meta}\nHeadings: {headings}\nContent: {text_block}"`.
   - **Strict Mode**: If crawl fails or returns no content, **skip LLM scoring** for this domain and record a `CrawlFailure` in the breakdown to prevent hallucinations.

4. **Build prompt** with all collected data, using `build_opportunity_prompt`.
   - **Anti-Hallucination**: The prompt includes strict instructions to return a 0 score and confidence 1 if no excerpt is provided and the domain name is not recognized with 100% certainty.

5. **Call scorer**: `OpportunityScorer().score_domain(context, excerpt)`
   - Returns `OpportunityScoreResult` or raises (we'll catch exceptions and convert to failure result).
   - On failure: log error, store `opportunity_breakdown = {"error": type, "message": str}`; preserve existing score unless none.

6. **Apply guardrail**:
   ```python
   if is_known_global_giant(domain) and result.opportunity_score > 20:
       final_score = 20
   else:
       final_score = result.opportunity_score
   ```

7. **Prepare update dict**:

```python
update = {
    "opportunity_score": final_score,
    "opportunity_breakdown": result.model_dump(),
    "opportunity_summary": result.one_sentence_summary,
    "opportunity_idea": result.romania_adaptation_idea,
    "opportunity_category": result.recommended_category,
    "opportunity_type": result.opportunity_type,
    "opportunity_confidence": result.confidence,
    "trend_score": computed_trend_score,
    "llm_opportunity_model": scorer.model,
    "llm_opportunity_prompt_version": "romania_llm_score_v1",
    "llm_opportunity_updated_at": datetime.utcnow().isoformat(),
}
```

8. **Persist**:
   - If `--dry-run`: log the update (pretty JSON) and skip DB write.
   - Else: `domain_repo.update_opportunity_fields(domain_id, update)` – add method to `DomainRepository`.

9. **Progress**: Print/log per domain and summary at end.

### Error Handling

- **LLM failure**: Catch `httpx.HTTPError`, `json.JSONDecodeError`, `ValidationError`, and generic exceptions. Store error in `opportunity_breakdown` field if slot available (JSONB can hold any dict). Do not crash.
- **Homepage fetch failure**: Log warning, proceed without excerpt.
- **Database errors**: Log and continue.

---

## 6. Dashboard UI Changes

### 6.1 Data Loading (`app/data_loader.py`)

- Modify the function that calls `get_domains_for_range` to accept and pass through the new opportunity parameters.
- Alternatively, since the RPC will now include opportunity fields by default, simply adjust any code that accesses domain dicts to use new keys.
- Provide helper functions for filter options:
  - `get_distinct_categories()` and `get_distinct_opportunity_types()` from database (or derive from loaded data).

### 6.2 Filters (`app/components/filters.py`)

Add widgets:

- **Min opportunity score**: `st.number_input("Min opportunity score", 0, 100, value=0)`
- **Min confidence**: `st.number_input("Min confidence", 0, 100, value=0)`
- **Hide global giants**: `st.checkbox("Hide global giants")` – filter inline after load (or add to RPC).
- **Opportunity category**: `st.multiselect("Category", options=category_list)`
- **Opportunity type**: `st.multiselect("Type", options=type_list)`
- **Not reviewed yet**: existing filter can be reused.

Filters applied client‑side on the DataFrame in `data_loader.py` (since dataset is modest). Keep chosen filters in `st.session_state` for persistence.

### 6.3 Domain Table (`app/components/domain_table.py`)

- Add columns to display:
  - `opportunity_score` (numeric)
  - `trend_score` (numeric)
  - `opportunity_category`
  - `opportunity_type`
  - `confidence`
  - `status`
- Default sorting: `opportunity_score` DESC, then `confidence` DESC, then `trend_score` DESC. Update the sort options list.
- Row expander (using `st.expander` or a button‑popover) to show:
  - **One‑sentence summary**
  - **Romania adaptation idea**
  - **Suggested MVP**
  - **Why it scores this way**
  - **Red flags** (bullet list)
  - **Full JSON breakdown** (pretty‑print with `st.json()`)

Implementation: iterate rows, for each domain show a row; inside, use `with st.expander("Details")` or a custom toggle if Streamlit permits. Simpler: add a new column with a "View" button that sets a session state to show a modal/dialog. But quick win: use `st.expander` per row may be heavy; alternative is a separate details section when a row is selected. For MVP, we can start with expander.

---

## 7. Guardrails and Edge Cases

### 7.1 Global Giant Cap

```python
from src.domains.normalize import is_known_giant

def apply_giant_cap(domain: str, score: int) -> int:
    if is_known_giant(domain) and score > 20:
        return 20
    return score
```

We will extend `KNOWN_GIANTS` in `src/config/constants.py` or create a separate giant list in `opportunity/constants.py`. The `is_known_giant` function already uses `KNOWN_GIANTS`. We'll add the additional giant domains there.

### 7.2 LLM Failure Fallback

- On failure, do **not** update `opportunity_score` (keep existing if any). If no existing score, set to `0` or `NULL`? We'll set to `0` to indicate unknown, or leave `NULL`. Safer: leave unchanged if existed; if missing, set to `0` with `opportunity_breakdown` containing error info.
- Log error message with domain name.

### 7.3 Dry Run

- Avoid side effects: no DB updates, no homepage fetching (network I/O).
- Print planned updates to stdout for review.

### 7.4 Rate Limiting Concurrency

- Use `asyncio.Semaphore` default 5 for concurrent LLM calls.
- Configurable via `--concurrency`.

---

## 8. Implementation Plan Summary

| Step | File(s) | Description |
|------|---------|-------------|
| **DB migration** | `supabase/schemas/004_opportunity_scores.sql` | Add columns to `domains` and update views |
| **Constants** | `src/opportunity/constants.py` | Global giants set |
| **Schemas** | `src/opportunity/schemas.py` | Pydantic model for LLM output |
| **Prompt** | `src/opportunity/prompt.py` | Prompt builder with all context fields |
| **Scorer** | `src/opportunity/scorer.py` | LLM client wrapper with retry/validation |
| **Command** | `src/opportunity/update_opportunity_scores.py` | Main CLI with argparse, domain loop, homepage fetching, persistence |
| **Entry point** | `main.py` | Top‑level command dispatcher |
| **Homepage fetch** | Within command module | Use `beautifulsoup4` (require `bs4`) |
| **Repo method** | `src/db/repositories.py` → `DomainRepository.update_opportunity_fields(...)` |
| **Views update** | `supabase/schemas/002_views.sql` | Add opportunity fields to views |
| **Dashboard** | `app/data_loader.py`, `app/components/filters.py`, `app/components/domain_table.py` | Show new columns, filters, expander |
| **Requirements** | `requirements.txt` | Add `beautifulsoup4` |
| **Tests** | `tests/opportunity/...` | As per spec (see §9) |

---

## 9. Testing Strategy

### Unit Tests
- **`test_prompt.py`**: Verify prompt includes all context fields for various input combinations.
- **`test_schemas.py`**: Valid JSON accepted; missing required fields rejected; extra fields rejected.
- **`test_scorer.py`**: Mock LLM responses (valid, invalid JSON, network errors). Verify retry logic and eventual failure result.
- **`test_guardrails.py``: Known giant domain scores capped at 20.
- **`test_homepage_fetch.py`**: Mock HTTP responses, extraction logic (title, meta, headings).
- **`test_command_args.py`**: Argparse parsing and filter logic.

### Integration Tests
- Score a sample set of domains with a mocked LLM (using `responses` or `httpx.MockTransport`) and verify DB writes (use a test Supabase instance or SQLite mock).
- Test `--dry-run`, `--only-missing`, `--force` behaviors.

### Manual QA
- Run command on a few real domains with `--dry-run` to inspect prompts and proposed scores.
- Verify dashboard displays new columns and sorting works.

---

## 10. Key Decisions & Trade‑offs

| Decision | Options Considered | Chosen | Reason |
|----------|-------------------|--------|--------|
| Store scores in separate table vs `domains` columns | Separate history table vs columns | Columns | Simpler; matches existing LLM enrichment pattern; overwrite acceptable |
| Category/type as JSON vs columns | Extract from JSONB vs separate columns | Separate columns | Simpler queries and UI dropdowns; better performance |
| Homepage parser | BeautifulSoup vs regex only | BeautifulSoup | More reliable extraction; worth adding `bs4` dependency |
| Command entry point | `./start` subcommand vs top‑level `main.py` | `main.py` (new) | Spec explicitly requires `python main.py update-opportunity-scores`; existing `./start` unchanged |
| LLM call concurrency | Sequential vs async/semaphore | Async with semaphore (CONCURRENCY=5) | Faster for batch scores; matches crawler pattern |
| Trend score source | `best_score_today` vs `best_score_week` | `best_score_today` (today's best) | Reflects current momentum; spec says "based on existing Cloudflare scoring" – today's score is the most direct |

---

## 11. Risks & Mitigations

| Risk | Impact | Mitigation |
|------|--------|------------|
| LLM quality mis‑aligned with Romania market | Low‑quality scores | Iterate on prompt; include many examples in `Update_scoring.md`; allow prompt versioning (`llm_opportunity_prompt_version`) to roll forward/back |
| Homepage fetching slows down command | Longer runtime | Make `--fetch-homepage` optional; default off; use concurrency limits |
| API failures (LMStudio down) | Incomplete batch | Retry with backoff; continue on failure; log errors |
| Database load (many writes) | Performance hit | Batch updates? Not necessary for occasional runs; single UPDATE per domain is fine |
| Global giant list incomplete | Some giants still get high scores | LLM should already penalize; cap adds safety; list can be updated later |

---

## 12. Acceptance Criteria Check (from spec)

1. ✅ `python main.py update-opportunity-scores` scores existing domains using an LLM.
2. ✅ Daily Cloudflare crawl remains separate (no performance impact).
3. ✅ LLM returns strict JSON (enforced by schema and retry).
4. ✅ System validates and stores output.
5. ✅ Stores all required fields (trend_score, opportunity_score, breakdown, summary, idea, model, prompt version, etc.).
6. ✅ Global giants capped at low scores (≤20).
7. ✅ Small, niche, foreign products can score high if they represent Romanian opportunities.
8. ✅ Existing domains can be rescored.
9. ✅ Dashboard sorts primarily by `opportunity_score`.
10. ✅ UI shows LLM reasoning and suggested MVP (expander).
11. ✅ Supports `--dry-run`, batch processing.
12. ✅ Handles LLM failures gracefully (continue, log, preserve old score).

All covered by design.

---

## 13. Open Questions (for implementation)

None; all design choices made per user's clarifications.

---

## 14. Next Steps

1. Write design document to `docs/superpowers/specs/2025-05-18-llm-opportunity-scoring-design.md`.
2. Obtain user approval.
3. Execute implementation plan using **writing-plans** skill.
4. Implement tests, run lint and type check.
5. Apply database migration.
6. Verify with dry‑run.
7. Update dashboard UI.
8. Manual testing and iteration on prompt quality.
