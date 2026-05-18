# Architecture

## Crawler Deduplication Cache & Async Bulk Writer

The crawler now loads all existing normalized domains into an in‑memory `set` at the start of each run. This cache enables O(1) deduplication checks, avoiding per‑record database lookups. New domains and observations are collected in memory and written in bulk using the asynchronous `post` helper from `src.db.async_client`. The bulk writer batches up to 800 rows per request (`bulk_upsert_domains` and `bulk_insert_observations` in `src.db.repositories`). Concurrency is controlled with an `asyncio.Semaphore` (default limit 10) and a shared `asyncio.Lock` protects the in‑memory buffers, ensuring safe parallel writes while respecting Supabase rate limits. This async bulk‑writer redesign reduces the daily crawl time from ~3 hours to ≤ 1 hour without schema changes or additional hardware.

## 1. High-Level System Diagram

**High-Level System Overview**

The UI layer consists of a Streamlit UI that communicates with Supabase via RPC calls. The backend layer includes a Crawl Orchestrator which fetches data from the Cloudflare Radar API, optionally enriches it using the LMStudio LLM Service, performs deduplication and scoring, and stores results in Supabase. External services are the Cloudflare Radar API and the LMStudio service.

**Explanation:** The UI (Streamlit) talks directly to Supabase via RPCs. A daily crawl job (`Crawl Orchestrator`) pulls data from Cloudflare, optionally enriches it with an LLM, processes domains through deduplication and scoring, and persists everything in Supabase.

## 2. Main Data Flow Diagram

**Main Data Flow Overview**

The UI (Streamlit) requests domain data via a Supabase RPC call, which runs a stored procedure in the database and returns a JSON payload for rendering. The crawler runs daily, fetching geolocation data from Cloudflare, then iterates over each country and ranking type to retrieve top domains. For each domain, deduplication is performed; new domains are enriched via the LMStudio client and scored before being upserted into Supabase, while duplicate domains only increment a duplicate counter.

**Explanation:** The UI layer reads pre-computed data from Supabase. The crawler pulls raw data from Cloudflare, deduplicates domains, runs LLM enrichment when configured, scores observations, and writes the results back to Supabase.

## Opportunity Scoring Command

Romanian-market opportunity scoring is implemented as a separate command. The crawler discovers and stores trend observations; the scoring command evaluates existing domains with LM Studio and writes `opportunity_score`, `opportunity_breakdown`, summary/idea fields, model metadata, and score status. The `./start crawler` wrapper runs `./start-score` after a successful crawl, while `./start crawler --skip-score` keeps the crawl-only flow.

Run scoring explicitly:

```bash
./start-score
```

The shortcut starts the local NVIDIA proxy, then runs `main.py update-opportunity-scores` with homepage fetching, `--only-missing`, domain concurrency `3`, LLM concurrency `1`, and model `meta/llama-3.1-8b-instruct`. The command uses LM Studio `json_schema` output with the `OpportunityScoreResult` schema. Failed attempts store `opportunity_score_status = 'failed'` plus `opportunity_score_error`, allowing `--only-missing` to skip permanent failures until `--force` is used.

## 3. Component / Module Diagram

**Component / Module Overview**

The system is organized into several Python classes:
- **StreamlitApp** runs the UI and delegates data loading to **DataLoader**.
- **DataLoader** provides methods to load collected data, today's data, statistics, and comments from Supabase via RPC calls.
- **CrawlOrchestrator** is the entry point for the crawling pipeline, coordinating country processing and invoking services.
- **RadarService** wraps calls to the **CloudflareClient**, which performs HTTP requests to the Cloudflare Radar API.
- **LMStudioClient** optionally enriches domains with LLM-generated data.
- **Deduplication** and **Scoring** contain the core business logic for deduping domains and scoring observations.
- Persistence is handled by repository classes (**DomainRepository**, **ObservationRepository**, **CrawlRunRepository**, **CrawlCountryStatusRepository**) that write to **SupabaseDB**, which stores tables such as `domains`, `domain_observations`, `crawl_runs`, and related views.
- The diagram originally visualized these relationships; the text above captures the same information in a format independent of any specific diagramming tool.

**Explanation:** This diagram shows the main Python modules and their responsibilities, plus the Supabase persistence layer.

## 4. Sequence Diagram - Main User Flow (Dashboard Load)

**Main User Flow (Dashboard Load) Overview**

When a user opens the local dashboard in a browser, the browser requests the initial page from the Streamlit server, which returns HTML and the Streamlit runtime. The browser then requests filtered data, prompting Streamlit to call the Supabase RPC `get_domains_for_range` with the selected filters. Supabase runs a stored procedure against the database, returning domain rows and counts as a JSON payload, which Streamlit uses to render tables, metrics, and charts in the browser.

**Explanation:** When a user opens the dashboard, Streamlit serves the page, fetches domain data via Supabase RPC, and renders the UI components.

## 5. Database Diagram

**Database Schema Overview**

The system uses several Supabase tables:
- **DOMAIN** stores unique domain records with fields such as `normalized_domain`, `display_url`, timestamps, initial score, review status, and various LLM‑generated attributes.
- **OBSERVATION** records a domain observation for a specific crawl run, linking to `DOMAIN` and `CRAWL_RUN` via foreign keys and containing details like date, country, ranking type, rank, percentage change, and observation score.
- **CRAWL_RUN** tracks each execution of the crawler, storing the run date, status, and start/finish timestamps.
- **CRAWL_COUNTRY_STATUS** records per‑country progress within a crawl run, including numbers of items found, new domains, and duplicates.
- **COMMENT** allows user‑generated comments attached to a domain.

Relationships: a domain has many observations; a crawl run produces many observations and tracks many country status records; a domain can have many comments.

These tables replace the previous Mermaid ER diagram with a plain textual description suitable for any documentation format.

**Explanation:** This diagram lists the primary Supabase tables and their relationships.

## 6. External Services Diagram

**External Services Overview**

The Crawl Orchestrator interacts with three external services:
- **Cloudflare Radar API** for geolocation (`GET /radar/geolocations`) and top‑ranking (`GET /radar/ranking/top`) data.
- **LMStudio LLM Service** to enrich domain information via an `enrich(domain)` call.
- **Supabase DB** where the crawler writes domain, observation, crawl‑run, and comment records.

This textual description replaces the previous Mermaid flowchart.

**Explanation:** Cloudflare provides ranking and geolocation data. LMStudio provides optional LLM enrichment. Supabase stores the processed results.

## 7. Detailed Crawl Pipeline Diagram

**Detailed Crawl Pipeline Overview**

1. **Create CrawlRun** – a new crawl run record is created.
2. **Fetch Country List** – the list of countries is retrieved from Cloudflare.
3. **Iterate Countries** – for each country, the orchestrator obtains top domains for each ranking type.
4. **Deduplication** – domains are checked; new domains proceed to enrichment, duplicates are counted.
5. **LLM Enrichment** (new domains only) – the domain is sent to the LMStudio service for enrichment.
6. **Scoring** – the enriched domain is scored.

**Scoring Mechanism Details**

The `score_observation()` function returns a `ScoreBreakdown` dataclass that records each component of the final observation score:
- **base** – a constant base score (`BASE_SCORE`).
- **ranking_type** – a bonus based on the ranking category (e.g., `global`, `country`) defined in `RANKING_TYPE_BONUS`.
- **rank** – a tiered bonus depending on the domain's rank, using `RANK_BONUS_TIERS`.
- **pct_rank_change** – a bonus proportional to the percentage rank change, capped by `PCT_RANK_CHANGE_MAX` and scaled by `PCT_RANK_CHANGE_DIVISOR`.
- **multi_country** – extra points for domains observed in multiple countries on the same day, limited by `MULTI_COUNTRY_MAX` and scaled by `MULTI_COUNTRY_PER_COUNTRY`.
- **category** – a bonus for the LLM‑identified category, looked up in `CATEGORY_BONUS`.
- **novelty** – a bonus for newly‑seen domains (`NOVELTY_FIRST_SEEN_TODAY` for same‑day, `NOVELTY_FIRST_SEEN_WEEK` for within a week).
- **llm_potential** – derived from the LLM idea potential rating (`(rating‑1) * 5`).
- **known_giant** – a penalty (`KNOWN_GIANT_PENALTY`) if the domain matches a known large entity (`is_known_giant`).
- **already_reviewed** – a penalty (`ALREADY_REVIEWED_PENALTY`) when the `review_status` indicates the domain was already reviewed (`ok`, `exists`, `bad`).

The final score is the sum of all positive components minus any penalties, accessible via `ScoreBreakdown.total`. The `details()` method returns a dictionary of each component for debugging and UI display.

7. **Insert Observation** – the observation is stored in Supabase.
8. **Update CrawlRun Progress** – progress counters are updated after each observation or duplicate.
9. **Check for Pause or Stop** – the orchestrator may pause, continue, or stop the crawl.
10. **Complete CrawlRun** – when stopped, the run is marked complete and final statistics are persisted.

This step‑by‑step description captures the same process without relying on Mermaid syntax.

**Explanation:** This shows each step of the daily crawl, including conditional LLM enrichment only for new domains and progress tracking.

## 8. Error Handling & Retry Diagram

**Error Handling & Retry Overview**

When the orchestrator requests top‑ranking data from Cloudflare and receives a `429 Too Many Requests` response, it logs a warning and retries the request using exponential backoff until a `200 OK` response is received. After obtaining the data, the orchestrator calls the LLM service to enrich a domain. If the LLM call fails (throws an exception), the orchestrator logs an error and records the observation in the database without the LLM‑generated fields. If the LLM call succeeds, the enrichment data is included in the upserted domain record.

**Explanation:** The orchestrator uses retry logic for Cloudflare calls. LLM enrichment failures are logged and the observation is still stored without LLM fields.

---

All diagrams are maintained as D2 source files in `docs/diagrams/` and rendered to SVG in `docs/diagrams/generated/`.
