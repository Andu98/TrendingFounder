Yes, makes sense. Then I’d change the architecture to:

```txt
Cloudflare crawl = finds trends
LLM scoring command = decides if it is a good Romania opportunity
Deterministic rules = only guardrails, not the main brain
```

Your app already has optional LMStudio enrichment in the crawler, but I would **not** put the new scoring inside the daily crawl. Keep it as a separate command, because your current pipeline already has crawler, deduplication, scoring, Supabase storage, and optional LLM enrichment.  Gemini’s plan also suggested an async/background scoring approach, but now the LLM becomes the main evaluator instead of just a future reranker. 

Give this updated plan to the agent:

````md
# Task: Replace Deterministic Opportunity Scoring With LLM-Based Romanian Market Opportunity Scoring

## Context

This project is a Python + Supabase + Streamlit app that discovers trending domains using Cloudflare Radar.

The current app:
- Crawls trending/top domains by country and ranking type.
- Deduplicates domains.
- Stores domains and observations in Supabase.
- Optionally enriches domains using LMStudio.
- Shows collected domains in a Streamlit dashboard.
- Currently has a scoring mechanism that recommends too many global giants like Amazon, Udemy, Box.com, Netflix, Booking, etc.

The goal is not to recommend the biggest websites on the internet.

The goal is to discover digital products, apps, SaaS tools, marketplaces, or business models that could inspire apps/services to build for the Romanian market.

The previous deterministic scoring plan is too rigid. Replace it with an LLM-first scoring system.

---

## Main Goal

Create a separate LLM-based opportunity scoring command:

```bash
python main.py update-opportunity-scores
````

This command should use an LLM to evaluate existing domains and assign a Romanian market opportunity score.

The score should answer:

"Is this domain/product/business model a realistic and interesting opportunity to adapt, clone, localize, or build for Romania?"

---

## Important Behavior

The command must work for both:

1. New domains discovered by future crawls.
2. Domains that already exist in Supabase.

Default behavior:

```bash
python main.py update-opportunity-scores
```

should process all existing domains that need scoring or rescoring.

Add optional flags:

```bash
python main.py update-opportunity-scores --only-missing
python main.py update-opportunity-scores --limit 500
python main.py update-opportunity-scores --min-trend-score 40
python main.py update-opportunity-scores --dry-run
python main.py update-opportunity-scores --force
```

Behavior:

* `--only-missing`: score only domains without an opportunity score.
* `--limit`: limit processed domains.
* `--min-trend-score`: only score domains above a trend threshold.
* `--dry-run`: print results without saving.
* `--force`: rescore even if already scored.

---

## Core Principle

Use the LLM as the main opportunity scorer.

Use deterministic logic only for:

* collecting cheap signals
* pre-filtering obvious junk
* passing context to the LLM
* fallback scoring if the LLM fails
* hard penalties for known global giants if needed

The LLM should decide the actual opportunity score.

---

## Scores To Store

Store two main scores:

```txt
trend_score
opportunity_score
```

### trend_score

This is based on the existing Cloudflare scoring logic:

* rank
* ranking type
* percentage rank change
* multi-country appearances
* novelty
* observations

This score measures raw trend/momentum.

### opportunity_score

This is produced by the LLM.

It measures how useful the domain is as inspiration for a Romanian-market app/business.

---

## Database Changes

Add these fields to the existing domains table or a related score table:

```sql
trend_score numeric
opportunity_score numeric
opportunity_score_breakdown jsonb
opportunity_summary text
opportunity_idea text
llm_score_model text
llm_score_prompt_version text
llm_score_updated_at timestamptz
```

If modifying `domains` is not clean, create:

```sql
domain_scores (
    id uuid primary key,
    domain_id uuid references domains(id),
    trend_score numeric,
    opportunity_score numeric,
    score_breakdown jsonb,
    opportunity_summary text,
    opportunity_idea text,
    llm_score_model text,
    llm_score_prompt_version text,
    created_at timestamptz,
    updated_at timestamptz
)
```

Prefer the simplest approach that matches the existing project style.

---

# LLM Scoring Rubric

The LLM should return a score from 0 to 100.

The score should reward domains that represent:

* realistic app ideas for Romania
* useful local adaptations
* underserved Romanian market needs
* buildable MVPs
* clear monetization
* non-obvious opportunities
* trends from countries similar to Romania
* B2B/SaaS/local services/marketplace ideas with practical demand

The score should penalize:

* global giants
* generic platforms
* already dominant categories
* ideas impossible for a small team
* products requiring massive capital
* products requiring huge network effects
* heavily regulated ideas
* vague content/media/social platforms
* pure hype
* ideas with no clear Romanian angle

---

## LLM Evaluation Dimensions

The LLM must evaluate each domain using these dimensions:

```json
{
  "romania_market_fit": 1,
  "local_gap": 1,
  "buildability": 1,
  "monetization_clarity": 1,
  "novelty": 1,
  "trend_relevance": 1,
  "competition_saturation": 1,
  "complexity": 1,
  "regulatory_risk": 1,
  "giant_or_too_generic": false
}
```

Scale:

* 1 = very weak
* 2 = weak
* 3 = medium
* 4 = strong
* 5 = very strong

For negative dimensions:

* `competition_saturation`: 1 means low saturation, 5 means very saturated.
* `complexity`: 1 means easy to build, 5 means very hard.
* `regulatory_risk`: 1 means low risk, 5 means high risk.

---

## Final LLM JSON Output

The LLM must return strict JSON only.

No markdown.
No comments.
No extra text.

Schema:

```json
{
  "opportunity_score": 0,
  "confidence": 0,
  "is_global_giant": false,
  "is_too_generic": false,
  "romania_market_fit": 1,
  "local_gap": 1,
  "buildability": 1,
  "monetization_clarity": 1,
  "novelty": 1,
  "trend_relevance": 1,
  "competition_saturation": 1,
  "complexity": 1,
  "regulatory_risk": 1,
  "recommended_category": "string",
  "opportunity_type": "string",
  "one_sentence_summary": "string",
  "romania_adaptation_idea": "string",
  "why_it_scores_this_way": "string",
  "red_flags": ["string"],
  "suggested_mvp": "string"
}
```

Field meaning:

* `opportunity_score`: integer from 0 to 100.
* `confidence`: integer from 0 to 100.
* `is_global_giant`: true for Amazon, Google, Netflix, Udemy, Booking, etc.
* `is_too_generic`: true for generic marketplaces, generic cloud storage, generic course platforms, generic social networks, etc.
* `recommended_category`: normalized category chosen by the LLM.
* `opportunity_type`: examples: `local_marketplace`, `b2b_saas`, `consumer_app`, `vertical_saas`, `content_platform`, `ecommerce_tool`, `education_tool`, `healthcare_tool`, `logistics_tool`.
* `one_sentence_summary`: what the domain/product appears to do.
* `romania_adaptation_idea`: how this could be adapted for Romania.
* `why_it_scores_this_way`: concise explanation.
* `red_flags`: risks or reasons to ignore it.
* `suggested_mvp`: practical MVP idea.

---

# LLM Prompt Template

Create a prompt builder, for example:

```txt
src/scoring/llm_opportunity_prompt.py
```

Use this prompt:

```txt
You are evaluating trending web domains as business/app inspiration for the Romanian market.

The goal is NOT to recommend the biggest websites.
The goal is to identify product ideas, SaaS tools, marketplaces, apps, or business models that could be adapted, localized, cloned, or built for Romania.

You must be strict. Penalize global giants and generic products heavily.

Evaluate the domain using only the provided data. Do not invent facts. If information is missing, say so and reduce confidence.

Romanian market preference:
- Reward small business tools.
- Reward local services.
- Reward home repair and service marketplaces.
- Reward medical/clinic booking or healthcare access tools.
- Reward education/reskilling tools if they are specific and buildable.
- Reward invoicing/accounting/payment tools if they are practical for Romanian businesses.
- Reward used/refurbished goods and value-focused commerce.
- Reward tourism/local experience ideas.
- Reward elderly/family care ideas.
- Reward B2B SaaS that solves concrete operational problems.

Penalize:
- global giants
- generic marketplaces
- generic course platforms
- generic cloud storage
- streaming platforms
- social networks
- crypto/Web3 hype
- ideas requiring massive inventory/logistics
- ideas requiring strong network effects from day one
- ideas already dominated by strong Romanian or global players
- ideas with unclear monetization

Domain data:
- domain: {{domain}}
- display_url: {{display_url}}
- trend_score: {{trend_score}}
- countries_observed: {{countries_observed}}
- ranking_types: {{ranking_types}}
- best_rank: {{best_rank}}
- pct_rank_change: {{pct_rank_change}}
- first_seen_at: {{first_seen_at}}
- existing_category: {{existing_category}}
- existing_summary: {{existing_summary}}
- existing_llm_potential: {{existing_llm_potential}}
- review_status: {{review_status}}
- romanian_signals: {{romanian_signals}}
- homepage_excerpt: {{homepage_excerpt}}

Return strict JSON only using this schema:

{
  "opportunity_score": 0,
  "confidence": 0,
  "is_global_giant": false,
  "is_too_generic": false,
  "romania_market_fit": 1,
  "local_gap": 1,
  "buildability": 1,
  "monetization_clarity": 1,
  "novelty": 1,
  "trend_relevance": 1,
  "competition_saturation": 1,
  "complexity": 1,
  "regulatory_risk": 1,
  "recommended_category": "string",
  "opportunity_type": "string",
  "one_sentence_summary": "string",
  "romania_adaptation_idea": "string",
  "why_it_scores_this_way": "string",
  "red_flags": ["string"],
  "suggested_mvp": "string"
}

Scoring guidance:
- 0-10: useless, giant, generic, irrelevant, or impossible
- 11-30: weak opportunity
- 31-50: maybe interesting but has serious issues
- 51-70: good opportunity worth reviewing
- 71-85: strong opportunity
- 86-100: exceptional Romania-focused opportunity

Be harsh with famous global platforms.
Amazon, Udemy, Box, Google, Netflix, Booking, Facebook, Instagram, YouTube, Apple, Microsoft, TikTok, Temu, AliExpress should score very low unless there is a very specific localizable niche pattern.
```

---

# LLM Client

Create or reuse an LLM client.

Suggested module:

```txt
src/scoring/llm_opportunity_scorer.py
```

Function:

```python
def score_domain_with_llm(domain, observations, homepage_excerpt=None) -> LlmOpportunityScore:
    ...
```

Requirements:

* Use the configured LLM provider.
* Support LMStudio/OpenAI-compatible local endpoint.
* Temperature should be low: 0 or 0.1.
* Validate JSON strictly.
* Retry once or twice if invalid JSON.
* If JSON is invalid after retries, store a failed score status or fallback.
* Do not crash the whole batch.
* Save raw response only if safe and useful for debugging.
* Store model name and prompt version.

Recommended config:

```env
OPPORTUNITY_SCORING_LLM_BASE_URL=http://localhost:1234/v1
OPPORTUNITY_SCORING_LLM_MODEL=qwen-or-other-local-model
OPPORTUNITY_SCORING_LLM_API_KEY=lm-studio
OPPORTUNITY_SCORING_PROMPT_VERSION=romania_llm_score_v1
```

---

# Deterministic Guardrails

Even though scoring is LLM-based, keep small deterministic guardrails.

Create:

```python
KNOWN_GLOBAL_GIANTS = {
    "amazon.com",
    "udemy.com",
    "box.com",
    "google.com",
    "youtube.com",
    "facebook.com",
    "instagram.com",
    "netflix.com",
    "booking.com",
    "airbnb.com",
    "microsoft.com",
    "apple.com",
    "temu.com",
    "aliexpress.com",
    "wikipedia.org",
    "linkedin.com",
    "x.com",
    "twitter.com",
    "tiktok.com"
}
```

If a domain is in this set:

* still call the LLM if needed
* but pass `known_global_giant = true` in the prompt
* optionally cap final `opportunity_score` at 20 unless the LLM gives a strong reason

Example:

```python
if is_known_global_giant and llm_score > 20:
    final_score = min(llm_score, 20)
else:
    final_score = llm_score
```

This prevents the LLM from being too generous.

---

# Optional Homepage Fetching

Add optional homepage fetching for better LLM context.

Command:

```bash
python main.py update-opportunity-scores --fetch-homepage
```

Rules:

* Fetch only homepage.
* Timeout: 5 seconds.
* Max response size: 500 KB.
* Extract title, meta description, headings, and first useful text blocks.
* Do not crawl multiple pages.
* Do not run this during the daily Cloudflare crawl.
* Cache homepage excerpts if possible.
* Ignore failures gracefully.

Pass this to the LLM as:

```txt
homepage_excerpt: ...
```

Without homepage fetching, use:

* domain name
* existing LLM enrichment
* Cloudflare observations
* category
* summary
* trend score
* countries observed

---

# Batch Command Behavior

The command:

```bash
python main.py update-opportunity-scores
```

should:

1. Load domains from Supabase.
2. Load recent observations for each domain.
3. Build scoring context.
4. Optionally fetch homepage excerpt.
5. Call the LLM.
6. Validate strict JSON output.
7. Apply deterministic caps/guardrails.
8. Save:

   * trend_score
   * opportunity_score
   * score_breakdown JSON
   * opportunity_summary
   * opportunity_idea
   * model name
   * prompt version
   * score timestamp
9. Continue even if some domains fail.
10. Print progress.

---

# Score Breakdown Storage

Store the full LLM output inside `opportunity_score_breakdown`.

Example:

```json
{
  "opportunity_score": 74,
  "confidence": 82,
  "is_global_giant": false,
  "is_too_generic": false,
  "romania_market_fit": 4,
  "local_gap": 4,
  "buildability": 4,
  "monetization_clarity": 4,
  "novelty": 3,
  "trend_relevance": 4,
  "competition_saturation": 2,
  "complexity": 2,
  "regulatory_risk": 1,
  "recommended_category": "local_services",
  "opportunity_type": "local_marketplace",
  "one_sentence_summary": "A platform that helps users book vetted home repair professionals.",
  "romania_adaptation_idea": "Build a Romanian marketplace for verified electricians, plumbers, and renovation workers with reviews, quotes, and WhatsApp-first booking.",
  "why_it_scores_this_way": "High local need, fragmented supply, clear monetization through leads or commissions, and feasible MVP.",
  "red_flags": ["Requires supply acquisition city by city"],
  "suggested_mvp": "Start in Bucharest with 3 categories: electricians, plumbers, and appliance repair.",
  "model": "qwen-local",
  "prompt_version": "romania_llm_score_v1"
}
```

---

# Dashboard/UI Changes

Update Streamlit to show:

Columns:

* domain / URL
* opportunity_score
* trend_score
* recommended_category
* opportunity_type
* countries found in
* ranking types
* confidence
* status
* comments

Default sorting:

1. `opportunity_score DESC`
2. `confidence DESC`
3. `trend_score DESC`

Add filters:

* minimum opportunity score
* minimum confidence
* hide global giants
* category
* opportunity type
* status
* country
* not reviewed yet

Add an expander/popover per row showing:

* one sentence summary
* Romania adaptation idea
* suggested MVP
* why it scored this way
* red flags
* full JSON breakdown

---

# Manual Review Feedback Loop

Use existing statuses:

* pending
* ok
* exists
* bad

Behavior:

* `bad`: deprioritize in UI.
* `exists`: show but lower priority.
* `ok`: keep visible.
* `pending`: default review queue.

Do not let manual status fully overwrite the LLM score, but use it in sorting/filtering.

Optional:

* If status is `bad`, skip rescoring unless `--force`.
* If status is `exists`, skip rescoring unless `--force`.

---

# LLM Failure Handling

If the LLM fails:

* do not crash the batch
* mark score status as failed
* keep old score if available
* log the error
* continue with next domain

Optional fallback:

* set opportunity_score to 0 only if there was no previous score
* store error in score_breakdown

Example:

```json
{
  "error": "invalid_json",
  "model": "qwen-local",
  "prompt_version": "romania_llm_score_v1"
}
```

---

# Tests

Add tests for:

1. Prompt builder includes all required domain context.
2. JSON parser accepts valid LLM output.
3. JSON parser rejects invalid output.
4. Global giants are capped at low opportunity scores.
5. Failed LLM calls do not crash the batch.
6. `--dry-run` does not write to Supabase.
7. `--only-missing` skips already scored domains.
8. `--force` rescores already scored domains.
9. Existing domains in Supabase can be scored, not just new ones.
10. UI can display opportunity score breakdown.

---

# Acceptance Criteria

The task is complete when:

1. `python main.py update-opportunity-scores` scores existing domains using an LLM.
2. The daily Cloudflare crawl does not become slower because LLM opportunity scoring is separate.
3. The LLM returns strict JSON.
4. The system validates and stores the LLM scoring output.
5. The app stores:

   * trend_score
   * opportunity_score
   * score breakdown
   * summary
   * Romania adaptation idea
   * suggested MVP
   * model name
   * prompt version
6. Amazon, Udemy, Box.com, Netflix, Booking, Google, etc. no longer rank as top opportunities.
7. Good localizable ideas can rank highly even if they are not globally huge.
8. Existing domains already in Supabase can be rescored.
9. The dashboard sorts primarily by opportunity_score.
10. The UI shows the LLM reasoning and suggested MVP.
11. The scoring command supports dry-run and batch processing.
12. The system handles LLM failures gracefully.

---

# Final Product Behavior

The app should stop behaving like:

"Here are the biggest websites on Earth."

It should behave like:

"Here are trending digital product patterns that may be worth adapting or building for Romania."

The LLM should act like a strict Romanian-market startup analyst.

A global giant can have a high trend score but should usually have a very low opportunity score.

A smaller, niche, foreign product can get a high opportunity score if it suggests a buildable, monetizable, locally relevant Romanian opportunity.

```
```
