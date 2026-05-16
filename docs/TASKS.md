# Tasks

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

- [x] **P5.01** — LM Studio OpenAI-compatible client (`src/llm/lmstudio_client.py`) with httpx, JSON response format, 60s timeout
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

- [x] **P7.01** — App entry point (`app/streamlit_app.py`) with navigation links and welcome page
- [x] **P7.02** — Today page (`app/pages/1_Today.py`) with filters, metrics cards, domain table placeholder
- [x] **P7.03** — This Week page (`app/pages/2_This_Week.py`) with filters, metrics, domain table placeholder
- [x] **P7.04** — Stats page (`app/pages/3_Stats.py`) with metric cards, progress bar, country progress table placeholder
- [x] **P7.05** — Metrics cards component (`app/components/metrics_cards.py`): render_metrics_cards, render_progress_bar
- [x] **P7.06** — Filters component (`app/components/filters.py`): show_reviewed checkbox, sort_by selectbox, min_score slider
- [x] **P7.07** — Domain table component (`app/components/domain_table.py`): st.dataframe with column config (LinkColumn, SelectboxColumn, etc.)
- [x] **P7.08** — Comments dialog component (`app/components/comments_dialog.py`): expander with comments list, timezone conversion to Europe/Bucharest, add comment form
- [x] **P7.09** — 3 tests for UI components
- [x] **P7.10** — Ruff per-file-ignores for N999 on Streamlit pages (numeric prefix naming)

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
