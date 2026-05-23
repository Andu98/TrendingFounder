# Tasks

- [x] **A2026-05-18.01** — Analyze current app crawling and scoring flow; findings written to `docs/APP_ANALYSIS_2026-05-18.md`.
- [x] **A2026-05-19.01** — Harden opportunity scoring: schema-constrained LM Studio responses, split domain/LLM concurrency, failure status persistence, homepage-miss scoring, and Supabase status migration.
- [x] **A2026-05-19.02** — Remove broken post-crawl opportunity scoring hook so crawls complete cleanly and scoring stays an explicit command.
- [x] **A2026-05-19.03** — Update README, runbook, architecture, prompt, and scoring design docs for the new opportunity scoring behavior.
- [x] **A2026-05-19.04** — Add `./start-score` shortcut that starts the NVIDIA proxy before running the default opportunity scoring command.
- [x] **A2026-05-19.05** — Make `./start crawler` run `./start-score` after successful crawls, with `--skip-score` for crawl-only runs.
- [x] **A2026-05-19.06** — Clarify zero-domain scoring runs and make `--only-missing --force` retry only failed missing-score rows.
- [x] **A2026-05-19.07** — Polish Streamlit dashboard UI: compact metrics, clearer empty state, notes action labels, global-giant pills, and structured opportunity details.
- [x] **A2026-05-19.08** — Redesign closed laptop domain cards with compact direct status actions and a cleaner notes panel.
- [x] **A2026-05-19.09** — Fix Streamlit production deprecations and add short dashboard read caching to reduce rerun blocking.
- [x] **A2026-05-19.10** — Add GitHub opencode repository discovery: schema, crawler, CLI wrapper, dashboard tab, review actions, and tests.
- [x] **A2026-05-19.11** — Make `./start-git-crawl` visible and faster with flushed progress output plus bulk GitHub repository and observation writes.
- [x] **A2026-05-20.01** — Make Collected Data status actions hide reviewed rows optimistically while Supabase writes finish in the background.
- [x] **A2026-05-20.02** — Add a GitHub Opencode "Mark all as seen" action that ignores all repositories in the current filtered view.
- [x] **A2026-05-20.03** — Default Collected Data to hide reviewed rows and load the full current month date range.
- [x] **A2026-05-20.04** — Keep Collected Data status changes optimistic in-session, set the snapshot flag at click time, reuse the current snapshot for the first rerun, and clear dashboard caches after the async Supabase write completes.
- [x] **A2026-05-20.05** — Remove stale test monkeypatches and verify the collected-data rerender path with the new snapshot helper.
- [x] **A2026-05-20.06** — Move Collected Data status actions onto Streamlit pre-render callbacks so production reruns can apply optimistic hiding before the full data load path.
- [x] **A2026-05-20.07** — Default Collected Data to 25 rows per page and reuse the comments snapshot during the one optimistic rerender after status changes.
- [x] **A2026-05-21.01** — Configure Streamlit websocket ping interval to reduce intermittent Uvicorn keepalive timeout noise in production logs.
- [x] **A2026-05-21.02** — Keep disconnected Streamlit browser sessions for 24 hours before server-side session cleanup.
- [x] **A2026-05-21.03** — Make GitHub Opencode `Seen` the first table column and apply seen checkbox edits through a pre-render callback so rows disappear immediately after marking.
- [x] **A2026-05-21.04** — Move Collected Data `Status` to the second visual column in the shared domain table header order.
- [x] **A2026-05-21.05** — Move the Collected Data status buttons into the second visual slot of each card so the layout matches the header order.
- [x] **A2026-05-21.06** — Align Collected Data CSS grid widths with the reordered row layout so the `Status` controls get the intended column width.
- [x] **A2026-05-21.07** — Add Impeccable project context files (`PRODUCT.md`, `DESIGN.md`, `.impeccable/design.json`) for future product UI work.
- [x] **A2026-05-21.08** — Make the selected Collected Data status button disabled and semantically colored to avoid no-op reruns and clarify the current review state.
- [x] **A2026-05-21.09** — Remove hover tooltips from Collected Data status buttons while keeping selected-state styling and no-op prevention.
- [x] **A2026-05-21.10** — Schedule the GitHub Actions crawl workflow for 07:00, 14:00, and 20:00 Europe/Bucharest with DST-safe UTC trigger candidates.
- [x] **A2026-05-23.01** — Remove the GitHub Actions runtime time gate so delayed scheduled starts still run the crawl pipeline, with four daily UTC triggers offset from minute 0.
- [x] **A2026-05-23.02** — Refill Collected Data with the next visible batch after optimistic status updates clear the current page.
- [x] **A2026-05-23.03** — Remove the versioned Streamlit config file after Community Cloud auto-update failures required manual reboot recovery.

- Implement async bulk DB client for domain deduplication and observation insertion.
- Load existing domains into memory at crawl start.
- Replace per‑record DB lookups with in‑memory set checks and batch inserts.
- Add async concurrency control for bulk operations.
- Update CI to include async test support (`pytest-asyncio`).
- Document the new deduplication cache and bulk writer in Architecture and Tasks docs.

## Phase 1: Foundation

Scop: proiectul pornește curat.

- [x] **P1.01** — Validate project skeleton matches PLAN.md structure
- [x] **P1.02** — Create settings loader (`src/config/settings.py`)
- [x] **P1.03** — Create constants file (`src/config/constants.py`)
- [x] **P1.04** — Setup logging (`src/utils/logging.py`)
- [x] **P1.05** — Validate `.env.example`
- [x] **P1.06** — Update `README.md`
- [x] **P1.07** — Populate `docs/AGENTS.md`
- [x] **P1.08** — Populate `docs/DECISIONS.md`
- [x] **P1.09** — Populate `docs/API_CONTRACTS.md`
- [x] **P1.10** — Initialize `docs/CHANGELOG.md`
- [x] **P1.11** — Run validation

---

## Phase 2: Cloudflare ingestion

- [x] **P2.01** — Add Cloudflare HTTP client with auth, retry, 429 handling (`src/cloudflare/client.py`)
- [x] **P2.02** — Verify Radar endpoints from official docs
- [x] **P2.03** — Implement geolocation fetch (`src/cloudflare/radar_service.py::get_geolocations`)
- [x] **P2.04** — Implement ranking fetch (`src/cloudflare/radar_service.py::get_top_domains`)
- [x] **P2.05** — Add Pydantic response schemas (`src/cloudflare/schemas.py`)
- [x] **P2.06** — Raw payload logging on failure
- [x] **P2.07** — Basic tests (20 tests total: client, service, schemas)

---

## Phase 3: Supabase schema

- [x] **P3.01** — `domains` table with unique normalized_domain, LLM fields, review_status enum
- [x] **P3.02** — `domain_observations` table with unique constraint (domain_id, observed_date, country_code, ranking_type)
- [x] **P3.03** — `crawl_runs` table with progress tracking counters
- [x] **P3.04** — `crawl_country_status` table with granular per-country progress
- [x] **P3.05** — `domain_comments` table for user notes
- [x] **P3.06** — Views: `v_domains_today`, `v_domains_this_week`, `v_crawl_stats`, `v_crawl_country_progress`
- [x] **P3.07** — RLS policies (placeholder full-access for internal tool)
- [x] **P3.08** — Supabase client wrapper (`src/db/supabase_client.py`)
- [x] **P3.09** — Repositories: Domain, Observation, CrawlRun, CrawlCountryStatus, Comment
- [x] **P3.10** — SQL queries module (`src/db/queries.py`)
- [x] **P3.11** — 13 new tests for all repository methods

---

## Phase 4: Deduplication

- [x] **P4.01** — `normalize_domain()` with tldextract for correct public suffix handling (co.uk, com.br, etc.)
- [x] **P4.02** — `build_display_url()` helper
- [x] **P4.03** — `is_known_giant()` check against constants list
- [x] **P4.04** — `dedupe_and_insert()` — upsert new domains, skip LLM for existing, always insert observation
- [x] **P4.05** — `DedupeResult` dataclass with domain_id, is_new flag, normalized_domain
- [x] **P4.06** — 24 new tests: 15 normalization edge cases, 3 dedupe scenarios, 6 display URL / giant checks

---

## Phase 5: LLM enrichment

- [x] **P5.01** — LM Studio OpenAI-compatible client (`src/llm/lmstudio_client.py`) with httpx, JSON response format, 300s timeout
- [x] **P5.02** — LLM response Pydantic schema (`src/llm/schemas.py`) with validation (scores 1-5, min-length summary, valid categories/business models)
- [x] **P5.03** — Enrichment prompt (`src/llm/prompts.py`) with strict JSON system prompt and dynamic field builder
- [x] **P5.04** — Parse/validate LLM response: strips markdown code blocks, validates JSON, validates Pydantic schema
- [x] **P5.05** — Fallback on LLM error: HTTP errors, invalid JSON, validation failures all return `LLMEnrichmentResult.failed()`
- [x] **P5.06** — Known giant annotation added to risk_notes
- [x] **P5.07** — 14 new tests: client HTTP error/invalid JSON/validation error/markdown stripping, prompt building, schema validation

---

## Phase 6: Scoring

- [x] **P6.01** — `score_observation()` engine with full breakdown from PLAN.md §10.1
- [x] **P6.02** — `ScoreBreakdown` dataclass with all component scores + total + details()
- [x] **P6.03** — Known giants penalty list (from constants)
- [x] **P6.04** — Category weights config (from constants)
- [x] **P6.05** — 31 new tests: base score, ranking type bonus, rank tiers, pct change, multi-country, category bonus/penalty, novelty, LLM potential, giant penalty, reviewed penalty, full calculation

---

## Phase 7: Streamlit UI

- [x] **P7.01** — Main Streamlit entry point (`app/streamlit_app.py`) with internal top navigation
- [x] **P7.02** — Collected Data tab with filters, responsive domain cards, inline review status updates, and comment popovers
- [x] **P7.03** — Reports tab with metric cards, crawl progress bar, and country-by-country status table
- [x] **P7.04** — Dark/light theme switcher with centralized CSS variables
- [x] **P7.05** — Metrics cards component (`app/components/metrics_cards.py`): render_metrics_cards, render_progress_bar
- [x] **P7.06** — Filters component (`app/components/filters.py`): date range, status checkboxes, category, sort, show reviewed
- [x] **P7.07** — Domain table component (`app/components/domain_table.py`): card rows with clickable domain, score badge, details expander, exclusive status checkboxes, comments popover
- [x] **P7.08** — Comments UX: timeline-style comment list plus add-comment form inside row popovers
- [x] **P7.09** — 3 tests for UI components
- [x] **P7.10** — Legacy Streamlit pages retained but no longer used as the primary navigation experience
- [x] **P7.11** — Dashboard visual polish: normal-scroll navbar, mobile burger menu, persistent theme state, consistent panel surfaces, wider content gutters, stacked mobile domain cards, and compact mobile table header
- [x] **P7.12** — Server-side Collected Data pagination and date range filtering via Supabase RPC (`get_domains_for_range`)
- [x] **P7.13** — Laptop domain card polish with direct status action buttons and redesigned notes popover

---

## Phase 8: Hardening

- [x] **P8.01** — Retry/backoff (already done in Phase 2: Cloudflare client with tenacity)
- [x] **P8.02** — 429 handling (already done in Phase 2: reads retry-after header)
- [x] **P8.03** — Crawl orchestrator (`src/crawler/orchestrator.py`): full pipeline from Cloudflare → dedupe → LLM → scoring → DB
- [x] **P8.04** — Daily crawl entry point (`src/crawler/run_daily.py`): CLI with --limit, --date, --skip-llm
- [x] **P8.05** — Progress tracker (`src/crawler/progress.py`): get_or_create_today_run, resume support, format_progress
- [x] **P8.06** — Run resume: detects existing running/partial runs and continues
- [x] **P8.07** — Partial failure support: crawl_run status = "partial" when some countries fail
- [x] **P8.08** — RUNBOOK.md: daily operations, troubleshooting, DB maintenance, monitoring
- [x] **P8.09** — 8 new tests: progress formatting, run resume logic, orchestrator end-to-end flow

---

## Phase 9: Documentation and Diagrams

- [x] **P9.01** — Install D2 diagramming tool via Homebrew
- [x] **P9.02** — Create system overview diagram (`docs/diagrams/system-overview.d2`) from existing architecture documentation
- [x] **P9.03** — Create external services diagram (`docs/diagrams/external-services.d2`) from existing architecture documentation  
- [x] **P9.04** — Create detailed crawl pipeline diagram (`docs/diagrams/crawl-pipeline.d2`) from existing architecture documentation
- [x] **P9.05** — Render all D2 diagrams to SVG format (`docs/diagrams/generated/`)
- [x] **P9.06** — Create diagrams README documenting the D2 setup and generation process
- [x] **P9.07** — Create opportunity scoring algorithm diagram (`docs/diagrams/scoring-algorithm.d2`) and render SVG.
