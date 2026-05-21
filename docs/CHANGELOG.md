# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

## [Unreleased]

### Added
- `.github/workflows/crawl.yml` — `workflow_dispatch` workflow that installs deps with uv and runs `./start crawler` + `./start-git-crawl`, with `skip_domain`, `skip_github`, `skip_score` inputs. Uploads `logs/` as an artifact.
- `src/integrations/github_actions.py` — helper to trigger and list runs of the workflow via the GitHub REST API. Reads `GH_REPO`, `GH_DISPATCH_TOKEN`, `GH_WORKFLOW_FILE`, `GH_WORKFLOW_REF` from env or `st.secrets`.
- Streamlit "Run Crawl" panel on the Reports page with a dispatch form and the last 5 runs.
- `.streamlit/secrets.toml.example` documenting the GH_* secrets.

### Changed
- Added `.streamlit/config.toml` with `server.websocketPingInterval = 60` so Streamlit's Uvicorn websocket timeout is less aggressive for slow, paused, or proxied browser connections.
- Set Streamlit `server.disconnectedSessionTTL = 86400` so disconnected browser sessions can retain server-side state for 24 hours before cleanup.
- Removed the local `nvidia-proxy.js` Node shim. `LMStudioClient` now sends `Authorization: Bearer $NVIDIA_API_KEY` directly to the OpenAI-compatible endpoint configured in `LMSTUDIO_BASE_URL` (default now `https://integrate.api.nvidia.com/v1`). `./start`, `./start-score`, and `./crawl` no longer launch a Node process.
- Collected Data status actions now optimistically hide reviewed rows when `Show reviewed` is off, set the snapshot flag at click time, reuse the current snapshot for the first rerun, and persist the review status to Supabase in the background with dashboard caches cleared after the async write completes.
- Collected Data status buttons now use Streamlit pre-render callbacks, so production reruns apply the optimistic hide state before blocking on the full Supabase fetch.
- Collected Data now defaults to 25 rows per page and reuses the comments snapshot for the one optimistic rerender after a status change, reducing the remaining production rerender work.
- Removed a stale `test_load_collected_data_calls_range_rpc` monkeypatch and added coverage for the one-rerun snapshot path used after status changes.
- GitHub Opencode now has a "Mark all as seen" action that marks every repository in the current filtered view as ignored.
- Collected Data now defaults to hiding reviewed rows and loading the full current month date range.

### Added
- Project skeleton with src/ package structure
- Settings loader via pydantic-settings
- Constants for ranking types, review status, scoring weights
- Loguru logging setup with console and rotating file sinks
- pyproject.toml with dependencies and tool config
- .env.example with documented variables
- README.md with quick start and project overview
- AGENTS.md with agent rules
- DECISIONS.md with ADR-001 through ADR-020
- API_CONTRACTS.md with Cloudflare Radar endpoint docs
- Initial TASKS.md phase checklist

### Phase 2: Cloudflare ingestion
- Cloudflare async HTTP client (`src/cloudflare/client.py`) with Bearer auth, tenacity retry/backoff, 429 rate-limit handling
- Radar service (`src/cloudflare/radar_service.py`) with `get_geolocations()` (filters COUNTRY type) and `get_top_domains()` (per location + ranking type)
- Pydantic response schemas (`src/cloudflare/schemas.py`) for geolocations and ranking/top endpoints
- Raw payload error logging on API failures
- 10 new tests: client auth/429/4xx, schema parsing, service geolocation filtering, ranking entry extraction
- pytest-asyncio added for async test support

### Phase 3: Supabase schema
- SQL schema `001_core.sql`: domains, domain_observations, crawl_runs, crawl_country_status, domain_comments tables with proper indexes and constraints
- SQL schema `002_views.sql`: v_domains_today, v_domains_this_week, v_crawl_stats, v_crawl_country_progress views, plus `get_domains_for_range(...)` RPC for server-side dashboard filtering/pagination
- SQL schema `003_rls.sql`: RLS policies (full-access placeholders for internal tool)
- Supabase client wrapper (`src/db/supabase_client.py`) using service role key
- Repository layer (`src/db/repositories.py`): DomainRepository, ObservationRepository, CrawlRunRepository, CrawlCountryStatusRepository, CommentRepository
- SQL queries module (`src/db/queries.py`) with named queries for dashboard views
- 13 new tests covering all repository CRUD operations

### Phase 4: Deduplication
- Domain normalization (`src/domains/normalize.py`) using tldextract for correct public suffix handling (co.uk, com.br, etc.)
- Dedupe logic (`src/domains/dedupe.py`): `dedupe_and_insert()` upserts new domains, skips LLM for existing, always inserts observation
- `DedupeResult` dataclass with domain_id, is_new flag, normalized_domain
- `build_display_url()` and `is_known_giant()` helpers
- 24 new tests: normalization edge cases (HTTPS, subdomains, international TLDs, invalid input), dedupe scenarios

### Phase 5: LLM enrichment
- LM Studio OpenAI-compatible client (`src/llm/lmstudio_client.py`) using httpx with `response_format: json_object`, 300s timeout
- LLM response Pydantic schema (`src/llm/schemas.py`) with score validation (1-5), min-length summary, valid category/business model constraints
- Enrichment prompt (`src/llm/prompts.py`) with strict JSON system prompt and dynamic field builder (title, meta description, categories, country, ranking, rank, pct change, homepage snippet)
- Response parsing: strips markdown code blocks, validates JSON, validates Pydantic schema
- Graceful fallback: HTTP errors, invalid JSON, validation failures return `LLMEnrichmentResult.failed()` with error details
- Known giant annotation appended to risk_notes
- 14 new tests: client error handling, prompt building, schema validation

### Phase 6: Scoring engine
- Scoring engine (`src/domains/scoring.py`): `score_observation()` with full `ScoreBreakdown` dataclass
- All scoring components implemented: base (20), ranking type bonus, rank tiers, pct rank change (capped at 20), multi-country bonus (capped at 20), category bonus/penalty, novelty (today=20, week=8), LLM potential (0-20), known giant penalty (-50), already reviewed penalty (-100)
- 31 new tests covering every scoring component and edge cases

### Phase 7: Streamlit UI
- App entry point (`app/streamlit_app.py`) with navigation links and welcome page
- Today page (`app/pages/1_Today.py`), This Week page (`app/pages/2_This_Week.py`), Stats page (`app/pages/3_Stats.py`) with filters, metrics, and placeholder tables
- Metrics cards component (`app/components/metrics_cards.py`): 4-column metric layout, progress bar
- Filters component (`app/components/filters.py`): date range, status checkboxes, category, sort, and show_reviewed controls
- Domain table component (`app/components/domain_table.py`): st.dataframe with LinkColumn, SelectboxColumn for status, column config
- Comments dialog component (`app/components/comments_dialog.py`): expander with comment list, Europe/Bucharest timezone conversion, add comment form
- 3 new tests for UI components
- Ruff per-file-ignores for N999 on Streamlit page files (numeric prefix naming convention)

### Phase 8: Hardening
- Crawl orchestrator (`src/crawler/orchestrator.py`): full pipeline — Cloudflare fetch → normalize → dedupe → insert observation → LLM enrichment (new domains only) → scoring → DB
- Daily crawl entry point (`src/crawler/run_daily.py`): CLI with `--limit`, `--date`, `--skip-llm` flags
- Progress tracker (`src/crawler/progress.py`): `get_or_create_today_run()` with resume detection, `format_progress()` for human-readable status
- Run resume: detects existing running/partial runs and continues from where it left off
- Partial failure support: crawl_run status set to "partial" when some countries fail but others succeed
- RUNBOOK.md: daily operations checklist, troubleshooting guide, DB maintenance queries, monitoring thresholds
- 8 new tests: progress formatting, run resume logic, orchestrator end-to-end flow with mocked dependencies

### Bug fixes & improvements
- **Opportunity scoring hardening**: Scoring now uses LM Studio `json_schema` output, defaults LLM calls to single concurrency via `--llm-concurrency`, retries only transient LM Studio failures, normalizes null required text fields, scores even when homepage fetch misses, and persists `opportunity_score_status` / `opportunity_score_error` for failed attempts.
- **`./start-score` shortcut**: Added a scoring launcher that starts the local NVIDIA proxy, waits for port `1234`, and runs the default opportunity scoring command. `run_scoring.sh` now delegates to it.
- **Post-crawl scoring wrapper**: `./start crawler` now runs `./start-score` after successful crawls. Use `./start crawler --skip-score` to keep crawl-only behavior.
- **Failed-score retry semantics fixed**: `--only-missing --force` now still filters to null `opportunity_score` rows and includes previously failed rows, instead of rescoring every domain. Zero-domain runs now log a clear `./start-score --force` retry hint when all missing rows are failed.
- **Streamlit dashboard polish**: Tightened card radii and row hover states, added focus treatment for inputs, replaced the empty-results info box with a domain-specific empty state, labeled comment actions as notes, marked known global giants, compacted report metric cards, and converted opportunity details into a structured panel.
- **Streamlit laptop card actions refreshed**: Replaced the closed-card status checkboxes with compact direct action buttons and redesigned the notes popover with a stronger header, empty state, and composer.
- **Streamlit production warnings fixed**: Replaced deprecated `use_container_width` calls with `width`, removed the deprecated HTML component usage, and added short TTL caching for dashboard Supabase reads with cache clearing after writes.
- **GitHub opencode discovery added**: Added separate GitHub Search API crawl flow, `github_*` Supabase schema, `./start-git-crawl`, baseline/new repository semantics, GitHub Opencode dashboard tab, inline review/notes actions, and focused tests.
- **GitHub crawl progress and bulk writes**: `./start-git-crawl` now prints flushed progress while it works and persists repository snapshots plus observations in bulk, avoiding the silent multi-minute first-run path.
- **GitHub filtered bulk ignore**: GitHub Opencode can now mark all currently filtered repositories as seen in one action, using a bulk Supabase update.
- **Collected Data defaults updated**: The dashboard now starts with reviewed rows hidden and the date range set to the full current month.
- **Crawler completion fix**: Removed the broken post-crawl opportunity scoring hook that was nested after `return` and crashed completed crawls with `AttributeError`. Opportunity scoring remains an explicit follow-up command.
- **Scoring docs synced**: README, RUNBOOK, Architecture, prompt docs, and opportunity scoring design notes now document the split concurrency model, explicit scoring command, homepage-miss policy, and failure-status columns.
- **LM Studio `json_schema` fix**: Changed `response_format` from `{"type": "json_object"}` to `{"type": "json_schema", "json_schema": {...}}` — LM Studio requires OpenAI-compatible JSON schema format, not legacy `json_object`. Fixes 400 Bad Request on all LLM calls.
- **Graceful stop mechanism**: Added `.crawl_stop` file-based stop signal. Create the file in the project root to pause the crawl gracefully after the current country finishes. The run status is set to "partial" and can be resumed by running the crawl again.
- **Unparseable domain skip**: Cloudflare sometimes returns public suffixes as domains (e.g., `ac.za`). These now get skipped with a warning log instead of crashing the entire country. Argentina no longer fails.
- **Hardcoded country fallback**: When Cloudflare geolocations API returns <50 countries, the crawler falls back to a hardcoded list of 250 ISO country codes (including Zimbabwe).
- **Streamlit UI wired to Supabase**: Today, This Week, and Stats pages now read live data from Supabase views (`v_domains_today`, `v_domains_this_week`, `v_crawl_country_progress`).
- **Categories converted to dicts**: Pydantic `Category` objects are now converted to plain dicts before passing to the LLM client, avoiding serialization issues.
- **SQL view alias fixes**: Reserved PostgreSQL keywords (`do`, `cr`) replaced with safe aliases (`obs`, `runs`, `dom`) in `002_views.sql`.
- **`RankingMeta` None handling**: Added `field_validator` to allow `None` for optional list fields (`units`, `dateRange`).
- **`CrawlRunRepository.update_progress()`**: Added missing `countries_total` parameter.
- **`final_status` enum fix**: Orchestrator now uses `CrawlRunStatus` enum instead of raw strings for run completion status.
- **`app/data_loader.py`**: New module to load data from Supabase views into pandas DataFrames for Streamlit.
- **Docs populated**: README.md, AGENTS.md, API_CONTRACTS.md, DECISIONS.md (ADR-001 to ADR-020), RUNBOOK.md, TASKS.md all created with comprehensive content.
- **`.env.example` improved**: Added comments with links to where to get each credential.

### Bug fixes & improvements (session 2026-05-16)
- **Streamlit dashboard centralized**: `app/streamlit_app.py` is now the primary UX with top navigation for Collected Data and Reports. Legacy `app/pages/*` files are retained but no longer drive the main navigation.
- **Collected Data UI refreshed**: Added responsive domain cards, richer filters, clickable domain links, category/business-model pills, score badges, details expanders, inline exclusive status checkboxes, and comment popovers.
- **Collected Data server-side pagination**: Added date range filtering and 10 / 25 / 50 / 100 row pagination backed by the new `get_domains_for_range(...)` Supabase RPC, so the dashboard only loads the current page of domains.
- **Reports tab added**: Replaces the old Stats page in the main UX with metric cards, crawl progress, and country-by-country crawl status rows.
- **Theme switcher added**: Top navbar includes light/dark mode with centralized Streamlit CSS variables and improved input/toggle/card contrast.
- **Dashboard visual polish**: Fixed main app scrolling, switched the navbar back to normal page flow, added a mobile burger menu with navigation and Dark mode controls, tightened page top spacing, and restored stacked mobile domain cards with a compact mobile header.
- **Theme persistence improved**: Dark/light preference now survives refreshes via URL query state plus browser storage sync, avoiding the previous refresh mismatch.
- **Collected Data surface consistency**: Filters panel now uses the same dark surface treatment as Reports cards while row Details expanders keep their nested style.
- **Crawl resume wired into orchestrator**: Orchestrator now uses `get_or_create_today_run()` instead of `create_run()`. On restart, skips already-completed/failed countries. (`src/crawler/orchestrator.py`, `src/crawler/progress.py`, `src/db/repositories.py`)
- **`CrawlCountryStatusRepository.get_country_statuses_for_run()`**: New method to query processed countries for a given run, enabling resume support.
- **`pytest-asyncio` upgraded** 0.25.0 → 1.3.0 — fixes 92 `DeprecationWarning`s on Python 3.14+.
- **Streamlit `page_link` paths fixed**: Changed `app/pages/...` → `pages/...` (relative to entrypoint directory).
- **`ButtonColumn` removed**: Streamlit 1.57.0 doesn't have `ButtonColumn`; replaced with `TextColumn` in `domain_table.py`.
- **LM Studio client retry**: Extracted `_post()` method with tenacity retry (4 attempts, exponential backoff 2-30s) for transient HTTP errors, matching Cloudflare client pattern. (`src/llm/lmstudio_client.py`)
- **Stats page fixed**: Replaced broken local `load_stats()` (queried with `None` date) with `data_loader.load_stats()`. (`app/pages/3_Stats.py`)
- **Domain table rewritten**: Replaced `st.data_editor` with manual per-row rendering using `st.columns`. Added inline exclusive status checkboxes and `st.popover` for Comments per row. `load_comments()` added to `data_loader`. (`app/components/domain_table.py`, `app/data_loader.py`)
- **`high_score_today` un-hardcoded**: Now queries `v_domains_today` for actual count instead of always showing 0. (`app/pages/1_Today.py`, `app/pages/3_Stats.py`)
- **Docs updated**: README phase statuses corrected, PLAN.md structure tree synced with codebase, TASKS.md got consistent `PX.XX` numbering.


### Phase 9: Documentation and Diagrams
- **D2 diagrams added**: Created system architecture diagrams using D2 (modern text-to-diagram language), including system-overview.d2, external-services.d2, and crawl-pipeline.d2 from existing architecture documentation.
- **Opportunity scoring diagram added**: Added `docs/diagrams/scoring-algorithm.d2` and rendered `docs/diagrams/generated/scoring-algorithm.svg` for the scoring command flow.
- **SVG rendering**: All diagrams are rendered to SVG format in docs/diagrams/generated/ for easy viewing and embedding.
- **Documentation**: Added comprehensive README in docs/diagrams/ explaining D2 installation, diagram generation, and reference to original architecture docs.
- **Task tracking**: Updated TASKS.md with new Phase 9 tracking all diagram-related activities.

(End of file - total 116 lines)
