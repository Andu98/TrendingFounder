# TrendingFounder — Project Context for AI Tools

## Overview

TrendingFounder discovers trending domains globally via Cloudflare Radar, deduplicates them, enriches with a local LLM (LM Studio), and presents them in a Streamlit dashboard for triage.

---

## Tech Stack

| Layer | Technology |
|---|---|
| Language | Python ≥ 3.14 |
| UI | Streamlit ≥ 1.57 |
| Database | Supabase (PostgreSQL) |
| LLM | LM Studio (OpenAI-compatible, local) |
| API source | Cloudflare Radar API |
| HTTP client | httpx (async) |
| Validation | Pydantic v2 |
| Config | pydantic-settings + .env |
| Logging | loguru |
| Tests | pytest + pytest-asyncio |
| Domain parsing | tldextract |

---

## Database Schema

### Table: `domains`

One row per unique normalized domain.

| Column | Type | Notes |
|---|---|---|
| id | UUID | PK, auto-generated |
| normalized_domain | TEXT | UNIQUE, e.g. `fanvue.com` |
| display_url | TEXT | e.g. `https://fanvue.com` |
| first_seen_at | TIMESTAMPTZ | |
| first_seen_date | DATE | |
| first_country_code | TEXT | e.g. `US` |
| first_country_name | TEXT | e.g. `United States` |
| first_ranking_type | TEXT | `POPULAR`, `TRENDING_RISE`, `TRENDING_STEADY` |
| llm_summary | TEXT | LLM output: short site summary |
| llm_category | TEXT | One of: AI, SaaS, Ecommerce, Community, Entertainment, Finance, Education, Productivity, Developer Tools, Marketplace, Games, Social, Adult, Gambling, Piracy, Scam-risk, Other |
| llm_business_model | TEXT | One of: ads, subscription, marketplace, ecommerce, lead_generation, unknown |
| llm_target_users | TEXT | LLM output |
| llm_localization_angle | TEXT | LLM output: how to adapt for Romania |
| llm_risk_notes | TEXT | LLM output: risk warnings |
| initial_score | NUMERIC | Score at first discovery |
| latest_best_score | NUMERIC | Best score across observations |
| review_status | TEXT | Enum: `pending`, `ok`, `exists`, `bad`. Default `pending` |
| reviewed_at | TIMESTAMPTZ | Nullable |
| reviewed_by | TEXT | Nullable |
| created_at | TIMESTAMPTZ | Auto |
| updated_at | TIMESTAMPTZ | Auto |

### Table: `domain_observations`

One row per appearance of a domain in a specific country/day/ranking type.

| Column | Type | Notes |
|---|---|---|
| id | UUID | PK |
| domain_id | UUID | FK → domains.id |
| crawl_run_id | UUID | FK → crawl_runs.id, nullable |
| observed_date | DATE | |
| observed_at | TIMESTAMPTZ | |
| country_code | TEXT | e.g. `US` |
| country_name | TEXT | |
| ranking_type | TEXT | Enum: `popular`, `trending_rise`, `trending_steady` |
| rank | INTEGER | Position in ranking |
| pct_rank_change | NUMERIC | Nullable. Only for TRENDING types |
| categories | JSONB | Cloudflare category IDs/names |
| observation_score | NUMERIC | Computed score for this observation |
| raw_payload | JSONB | Raw API response for debugging |
| created_at | TIMESTAMPTZ | |

Unique constraint: `(domain_id, observed_date, country_code, ranking_type)`

### Table: `crawl_runs`

Tracks each daily crawl execution.

| Column | Type | Notes |
|---|---|---|
| id | UUID | PK |
| run_date | DATE | UNIQUE |
| status | TEXT | Enum: `pending`, `running`, `completed`, `failed`, `partial` |
| started_at | TIMESTAMPTZ | |
| finished_at | TIMESTAMPTZ | Nullable |
| countries_total | INTEGER | |
| countries_completed | INTEGER | |
| countries_failed | INTEGER | |
| requests_total | INTEGER | |
| requests_failed | INTEGER | |
| new_domains_count | INTEGER | |
| duplicate_domains_count | INTEGER | |
| llm_processed_count | INTEGER | |
| llm_skipped_count | INTEGER | |
| error_message | TEXT | Nullable |
| created_at | TIMESTAMPTZ | |
| updated_at | TIMESTAMPTZ | |

### Table: `crawl_country_status`

Granular progress per country per run.

| Column | Type | Notes |
|---|---|---|
| id | UUID | PK |
| crawl_run_id | UUID | FK → crawl_runs.id |
| country_code | TEXT | |
| country_name | TEXT | |
| status | TEXT | Enum: `pending`, `running`, `completed`, `failed` |
| started_at | TIMESTAMPTZ | Nullable |
| finished_at | TIMESTAMPTZ | Nullable |
| error_message | TEXT | Nullable |
| items_found | INTEGER | |
| new_domains | INTEGER | |
| duplicate_domains | INTEGER | |

Unique constraint: `(crawl_run_id, country_code)`

### Table: `domain_comments`

User notes per domain.

| Column | Type | Notes |
|---|---|---|
| id | UUID | PK |
| domain_id | UUID | FK → domains.id |
| author_name | TEXT | |
| message | TEXT | |
| created_at | TIMESTAMPTZ | |

---

## Views

### `v_domains_today`

Returns domains with observations from today, aggregated per domain.

Columns: `id`, `normalized_domain`, `display_url`, `first_seen_date`, `llm_summary`, `llm_category`, `llm_business_model`, `review_status`, `initial_score`, `latest_best_score`, `best_score_today` (MAX of observation_score), `countries_today` (COUNT DISTINCT country), `ranking_types_count`, `country_codes` (array), `ranking_types` (array), `comment_count`

### `v_domains_this_week`

Same shape as `v_domains_today` but filtered to last 7 days. Extra columns: `first_seen_in_week`, `last_seen_in_week`, `times_observed`.

### `v_crawl_stats`

Aggregated metrics from `crawl_runs` + derived counts.

Columns: `run_date`, `crawl_status`, `countries_total`, `countries_completed`, `countries_failed`, `requests_total`, `requests_failed`, `new_domains_count`, `duplicate_domains_count`, `llm_processed_count`, `llm_skipped_count`, `started_at`, `finished_at`, `new_domains_today`, `observations_today`, `reviewed_today`, `reviewed_total`, `high_score_today`

### `v_crawl_country_progress`

Per-country status for today's run.

Columns: `crawl_run_id`, `run_date`, `crawl_status`, `country_code`, `country_name`, `country_status`, `started_at`, `finished_at`, `error_message`, `items_found`, `new_domains`, `duplicate_domains`

---

## Scoring Engine

Score formula:
```
score = base_score (20)
      + ranking_type_bonus (TRENDING_RISE=30, TRENDING_STEADY=18, POPULAR=5)
      + rank_bonus (rank 1-10=20, 11-25=12, 26-50=7, 51-100=3)
      + pct_rank_change_bonus (min(20, pctChange/5))
      + multi_country_bonus (+2/country today, max 20)
      + category_bonus (AI/SaaS/Productivity/Education/DevTools=15, Ecommerce/Marketplace/Finance=10, Entertainment/Games/Social=5, Adult/Gambling/Piracy/Scam-risk=-30)
      + novelty_bonus (first_seen_today=20, this_week=8, older=0)
      + llm_potential_bonus (idea_potential 1-5 → 0,5,10,15,20)
      - known_giant_penalty (google.com, youtube.com, etc. = -50)
      - already_reviewed_penalty (ok/exists/bad = -100)
```

Known giants list: google.com, youtube.com, facebook.com, amazon.com, microsoft.com, apple.com, cloudflare.com, twitter.com, x.com, instagram.com, tiktok.com, netflix.com, wikipedia.org, reddit.com, linkedin.com, whatsapp.com, zoom.us, slack.com, github.com, stackoverflow.com

---

## LLM Enrichment

**Endpoint:** LM Studio on `http://localhost:1234/v1/chat/completions`
**Model:** `qwen/qwen2.5-vl-7b`
**Response format:** `json_schema` with strict schema
**Timeout:** 60s
**Retry:** 4 attempts, exponential backoff 2-30s (on HTTP errors, connect errors, timeouts)

**Input fields sent to LLM:**
- domain, title, meta_description, Cloudflare categories, country_code, ranking_type, rank, pct_rank_change, homepage_snippet (up to 4KB)

**LLM output (validated JSON):**

| Field | Type | Constraints |
|---|---|---|
| summary | string | 1-500 chars |
| category | string | One of valid categories list |
| business_model | string | One of valid business models list |
| target_users | string | 1-300 chars |
| localization_angle | string | 1-300 chars |
| risk_notes | string | 0-500 chars |
| novelty | integer | 1-5 |
| idea_potential | integer | 1-5 |
| confidence | integer | 1-5 |

---

## Cloudflare Radar API

**Endpoint:** `GET https://api.cloudflare.com/client/v4/radar/ranking/top`

**Query params:** `location` (country alpha-2), `rankingType` (POPULAR/TRENDING_RISE/TRENDING_STEADY), `limit` (default 100), `format` (JSON), `date` (optional YYYY-MM-DD)

**Auth:** Bearer token in `Authorization` header

**Rate limit:** 1200 requests / 5 minutes per token

**Response shape:** `result.meta` + `result.top_0[]` with fields: `domain`, `rank`, `pctRankChange` (only for TRENDING types), `categories[]`

---

## Crawl Pipeline (Daily)

1. Create/resume `crawl_run` (detect partial runs, skip completed countries)
2. Fetch geolocations from Cloudflare (filter COUNTRY type only)
3. For each country (sequential, not parallel):
   - Fetch TRENDING_RISE domains
   - Fetch TRENDING_STEADY domains
   - Normalize domain → registrable domain (tldextract)
   - Dedupe: if new → insert domain + run LLM + score; if existing → insert observation only (skip LLM)
   - Update country status in DB
4. Mark run as completed / partial / failed

---

## Streamlit UI

The visible dashboard is centralized in `app/streamlit_app.py`. The legacy files under `app/pages/` can remain for reference, but the primary UX is not the Streamlit sidebar multipage navigation.

### Collected Data tab
- Default active tab when the app opens
- Header: "Collected Data" plus total filtered domain count from the server-side query
- Filters: date range, review status checkboxes, category, sort, show reviewed
- Pagination: 50 rows by default, with 10 / 25 / 50 / 100 row options
- Domain cards: clickable domain URL, category pill, business-model pill when known, score badge, summary, first country, inline exclusive status checkboxes, comments popover
- Details expander: countries found in, ranking types, target users, localization angle, risk notes, first seen, first/last seen in range, times observed, initial score
- Review status persists through `DomainRepository.update_review_status()`
- Comments persist through `CommentRepository.add_comment()`

### Reports tab
- Replaces the old Stats page as the main crawl reporting surface
- Metrics: Countries Crawled, New Domains, Duplicates, LLM Processed, High Score, Reviewed
- Crawl progress bar: countries_completed / countries_total
- Country-by-country status table with visually distinct status pills

### Theme
- Top navbar includes a dark/light mode switcher
- CSS is centralized in `streamlit_app.py` through theme variables
- Default theme is dark

---

## Streamlit Page Structure

```
app/
  streamlit_app.py          # Primary single-screen app, top nav, theme CSS
  data_loader.py            # load_collected_data(), load_today_data(), load_stats(), load_comments(), load_high_score_count()
  components/
    domain_table.py         # render_domain_table() — manual row rendering with inline editing
    filters.py              # render_filters() — date range/status checkboxes/category/sort/show reviewed
    metrics_cards.py        # render_metrics_cards(), render_progress_bar()
    comments_dialog.py      # (deprecated — inline popovers used instead)
  pages/
    1_Today.py              # Legacy page, not primary UX
    2_This_Week.py          # Legacy page, not primary UX
    3_Stats.py              # Legacy page, not primary UX
```

---

## .env Configuration

```
CLOUDFLARE_API_TOKEN=       # Cloudflare API token with Radar read
SUPABASE_URL=               # https://<project>.supabase.co
SUPABASE_ANON_KEY=          # Publishable anon key
SUPABASE_SERVICE_ROLE_KEY=  # Service role key (server-side)
LMSTUDIO_BASE_URL=          # Default: http://localhost:1234/v1
LMSTUDIO_MODEL=             # Default: qwen/qwen2.5-vl-7b
APP_TIMEZONE=               # Default: Europe/Bucharest
LOG_LEVEL=                  # Default: INFO
```

---

## CLI Usage

```bash
python -m src.crawler.run_daily                    # Full crawl
python -m src.crawler.run_daily --limit 50         # Limit domains per country
python -m src.crawler.run_daily --date 2026-05-15  # Specific date
python -m src.crawler.run_daily --skip-llm         # No LLM enrichment
./start trending                                   # Launch dashboard via local .venv or uv
./start trending --server.port 8502                # Launch dashboard on another port
```
