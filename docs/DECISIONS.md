# Architecture Decision Records

## ADR-001: Use domains + domain_observations instead of one flat table

**Status:** Accepted

One row per unique domain in `domains`, plus one row per appearance in `domain_observations`. This avoids duplicate rows in the UI while preserving full history for scoring and analytics.

## ADR-002: Run LLM only once per normalized domain

**Status:** Accepted

LLM enrichment runs only when a normalized domain does not already exist in the `domains` table. Subsequent appearances only insert a new observation. This saves cost and avoids inconsistent summaries.

## ADR-003: Store timestamps in UTC, display Europe/Bucharest in UI

**Status:** Accepted

All database timestamps use `timestamptz` (UTC). Conversion to `Europe/Bucharest` happens only at the presentation layer (Streamlit).

## ADR-004: Store review status as enum, not 3 booleans

**Status:** Accepted

`review_status` is a single enum column (`pending | ok | exists | bad`). UI may show 4 exclusive checkboxes, but they map to this single field on save.

## ADR-005: Use Cloudflare Markdown docs as API source of truth

**Status:** Accepted

Cloudflare provides Markdown documentation for agents. This is the authoritative source for endpoint paths, parameters, and response shapes — not guesswork or third-party blogs.

## ADR-006: Use Streamlit for MVP despite mobile limitations

**Status:** Accepted

Streamlit is chosen for speed of development. Mobile responsiveness is not perfect but acceptable for MVP. Can be replaced later if needed.

## ADR-007: Use loguru for logging

**Status:** Accepted

`loguru` is used instead of Python's standard `logging` module for simpler configuration, better formatting, and built-in rotation/retention support.

## ADR-008: Use pyproject.toml as single source of truth for project config

**Status:** Accepted

`pyproject.toml` holds project metadata, dependencies, and tool configuration (ruff, black, pytest). `requirements.txt` is kept as a frozen lockfile reference but pyproject.toml is the source of truth.

## ADR-009: Package name is TrendingFounder with src/ subpackages

**Status:** Accepted

The importable package is `src` with subpackages (`src.config`, `src.cloudflare`, etc.) matching the PLAN.md structure. Project name in pyproject.toml is `trendingfounder`.

## ADR-010: Use async HTTP client (httpx) for Cloudflare API calls

**Status:** Accepted

`httpx.AsyncClient` is used instead of synchronous `requests` for Cloudflare API calls. This enables concurrent requests for the daily crawl (200+ countries × 2 ranking types) without thread overhead. The client uses `tenacity` for retry with exponential backoff and handles 429 rate-limit responses by reading the `retry-after` header.

## ADR-011: Use pytest-asyncio for async test support

**Status:** Accepted

`pytest-asyncio` in `auto` mode is used so that any `async def test_*` function is automatically run with an event loop. This avoids the need for `@pytest.mark.asyncio` decorators on every test.

## ADR-012: Use Supabase service role key for backend operations

**Status:** Accepted

The Supabase client uses `supabase_service_role_key` (not the anon key) because this is a backend/internal tool. The service role key bypasses RLS, which is appropriate since the application itself enforces all business logic. RLS policies are still defined as a safety layer and for future multi-user scenarios.

## ADR-013: Repository pattern for database access

**Status:** Accepted

A repository layer (`src/db/repositories.py`) wraps the Supabase Python client. Each table has a dedicated repository class with typed methods. This keeps SQL/PostgREST queries out of business logic and makes testing easier via mock injection.

## ADR-014: Declarative SQL schemas over migration framework

**Status:** Accepted

SQL files in `supabase/schemas/` define the desired state (`001_core.sql`, `002_views.sql`, `003_rls.sql`). These are `CREATE IF NOT EXISTS` / `CREATE OR REPLACE` statements that can be applied idempotently. This matches Supabase's declarative schema approach and avoids migration complexity during MVP development.

## ADR-015: Use tldextract for domain normalization

**Status:** Accepted

`tldextract` is used instead of simple string splitting to correctly handle public suffix lists (e.g., `example.co.uk` → `example.co.uk`, not `co.uk`). This prevents incorrect deduplication for domains with multi-part TLDs. Domains without a valid TLD suffix raise `ValueError`.

## ADR-016: Use httpx directly for LM Studio instead of openai SDK

**Status:** Accepted

LM Studio provides an OpenAI-compatible endpoint. Rather than adding the `openai` package as a dependency, we use `httpx` directly to POST to `/chat/completions` with `response_format: {"type": "json_schema", "json_schema": {...}}`. This keeps the dependency tree smaller and gives full control over request/response handling. The JSON schema is derived from the `LLMEnrichmentResult` Pydantic model to ensure consistency.

## ADR-017: LLM enrichment never blocks the crawl pipeline

**Status:** Accepted

If the LLM request fails (HTTP error, timeout, invalid response, validation error), the crawl continues. The domain is marked with a failed enrichment result containing the error details. This ensures that a single LLM failure doesn't block processing of hundreds of domains.

## ADR-018: Scoring returns full breakdown, not just total

**Status:** Accepted

`score_observation()` returns a `ScoreBreakdown` dataclass with all component scores plus a `total` property and `details()` method. This makes scoring explainable and debuggable — users can see exactly why a domain got its score instead of treating it as a black box.

## ADR-019: Streamlit pages use numeric prefix naming convention

**Status:** Accepted

Legacy Streamlit page files use numeric prefixes (`1_Today.py`, `2_This_Week.py`, `3_Stats.py`) for ordering in the sidebar. This conflicts with Python's PEP 8 module naming convention, so Ruff's `N999` rule is ignored for `app/pages/*.py` files via `per-file-ignores` in `pyproject.toml`.

These files are retained for compatibility/reference, but the primary dashboard UX is now centralized in `app/streamlit_app.py` with internal top navigation.

## ADR-020: Orchestrator processes countries sequentially, not in parallel

**Status:** Accepted

The crawl orchestrator processes countries one at a time rather than in parallel. This is intentional to:
1. Stay well within Cloudflare's rate limits (1200 req / 5 min)
2. Make progress tracking and partial failure handling simpler
3. Avoid overwhelming the LLM service with concurrent requests
4. Keep memory usage low (no need to buffer hundreds of responses)

For 210 countries × 2 ranking types = 420 requests, sequential processing at ~1 req/sec takes ~7 minutes, well within acceptable limits.

## ADR-021: Use file-based stop signal for graceful crawl pause

**Status:** Accepted

The crawl orchestrator checks for a `.crawl_stop` file at the start of each country iteration. If found, it deletes the file, saves progress to the DB with status "partial", and exits cleanly. This allows the user to pause a long-running crawl (250 countries × ~30s = ~2 hours) without losing progress. The crawl can be resumed by running the same command again — it will detect the partial run and skip already-processed countries.

A file-based signal was chosen over signal handlers (SIGUSR1) for simplicity and cross-platform compatibility (works on macOS, Linux, Windows).

## ADR-022: Use `json_schema` response format for LM Studio

**Status:** Accepted

LM Studio's OpenAI-compatible endpoint does not support the legacy `response_format: {"type": "json_object"}`. It requires `response_format: {"type": "json_schema", "json_schema": {...}}` with a full JSON Schema definition. The LLM client now sends the schema derived from `LLMEnrichmentResult` Pydantic model. This ensures the model returns correctly structured JSON every time.

## ADR-023: Skip unparseable domains instead of failing country

**Status:** Accepted

Cloudflare Radar sometimes returns public suffixes (e.g., `ac.za`) or other non-registrable domain strings in the trending domains list. `tldextract` correctly rejects these as they have no registrable domain part. Rather than crashing the entire country's processing, these entries are now skipped with a warning log. This ensures that a single bad domain doesn't cause 5-10 other valid domains from that country to be lost.

## ADR-024: Use a single Streamlit app with internal navigation

**Status:** Accepted

The main dashboard is centralized in `app/streamlit_app.py` instead of relying on Streamlit's sidebar multipage navigation. The app uses a top navbar with two internal tabs: Collected Data and Reports.

This keeps the first screen focused, avoids exposing legacy Today/This Week/Stats pages as the main UX, and allows shared theme styling, filters, domain cards, inline status updates, comments, and reports to live in one cohesive Streamlit experience.

## ADR-025: Constrain opportunity scoring separately from domain work

**Status:** Accepted

Opportunity score updates split domain-level concurrency from LM Studio concurrency. `--concurrency` controls local work such as context loading and homepage fetches, while `--llm-concurrency` controls model calls and defaults to `1` to avoid local LM Studio 429s.

Opportunity scoring uses `json_schema` response format with an explicit `OpportunityScoreResult` schema. Failed model calls are persisted with `opportunity_score_status = 'failed'` and `opportunity_score_error`, so `--only-missing` can avoid retrying permanent failures unless `--force` is used. Homepage fetch misses no longer skip scoring; they are logged and counted, then the domain is scored from existing observations and enrichment context.

The Python crawler does not embed opportunity scoring. The `./start crawler` operational wrapper runs `./start-score` after a successful crawl, and `./start crawler --skip-score` keeps a crawl-only path. This preserves module separation while making the default operator flow crawl then score.

## ADR-026: Keep GitHub opencode discovery separate from domain discovery

**Status:** Accepted

GitHub repository discovery is implemented as a separate pipeline from the Cloudflare domain crawler. It uses the GitHub Search API for `topic:opencode`, stores results in `github_*` tables, and exposes a dedicated `./start-git-crawl` command plus a GitHub Opencode dashboard tab.

The first run is treated as a baseline snapshot of the current top repositories by stars. Baseline rows are stored for future comparison but are not shown as new discoveries. Later runs compare `github_repo_id` values against existing rows and mark only previously unseen repositories with `is_new = true`.

Repository snapshots and observations are persisted in batches, and the CLI emits flushed progress messages. This keeps the first-run baseline from appearing stalled while avoiding hundreds of sequential Supabase requests.

This separation avoids mixing repository discovery with domain observations, prevents accidental LLM/scoring calls for GitHub data, and keeps review statuses domain-specific versus GitHub-specific.

## ADR-027: Prefer scheduled crawl execution over exact local-hour gating

**Status:** Accepted

The GitHub Actions crawl workflow runs on a single UTC cron entry and does not use a runtime Europe/Bucharest hour gate. GitHub can start scheduled workflows late, and a strict runtime-hour check can mark the workflow successful while skipping the actual crawl job.

The current schedule is `05:00`, `11:00`, `17:00`, and `23:00` UTC, which corresponds to `08:00`, `14:00`, `20:00`, and `02:00` Europe/Bucharest during daylight saving time. This favors reliably running the pipeline for each scheduled trigger over enforcing exact local wall-clock hours inside the workflow.
