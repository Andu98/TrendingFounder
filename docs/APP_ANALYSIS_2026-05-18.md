# App Analysis - Crawling and Scoring

Date: 2026-05-18

Scope: repository docs, crawler flow, deterministic scoring, LLM opportunity scoring, database mappings, recent logs, and test status.

Update on 2026-05-19: the highest-risk scoring issues from this analysis have been addressed. The crawler no longer calls the broken post-crawl opportunity scoring hook, opportunity scoring now uses LM Studio `json_schema`, `--llm-concurrency` defaults to 1, failed scores persist `opportunity_score_status` / `opportunity_score_error`, homepage misses score with existing context, and `supabase/schemas/004_opportunity_scores.sql` has been applied through Supabase MCP.

## Executive Summary

The product shape is clear and useful: Cloudflare Radar finds trending domains, Supabase stores unique domains plus repeated observations, deterministic scoring ranks raw trend momentum, and a separate LLM command scores Romanian-market opportunity.

The highest-risk issue is that the crawler currently does not complete cleanly when it discovers new domains. `CrawlOrchestrator.run()` calls `self._run_opportunity_scoring(...)`, but that method is accidentally nested after a `return` inside `run()` and is not a class method. The venv test run confirms this with `AttributeError`.

There is also significant drift between docs and implementation:

- ADR-020 says the crawler is sequential, but the implementation launches all countries through `asyncio.gather()` with `CRAWL_CONCURRENCY` defaulting to 8.
- `docs/Architecture.md` says the crawler uses an async bulk writer, but the hot path still uses per-domain synchronous repository upserts.
- `docs/Update_scoring.md` says homepage-fetch failure should skip scoring, but the current code scores without homepage and the logs show many low-context LLM calls.
- `--date` does not consistently control the crawl run date or Cloudflare date query.

Operationally, the current scoring run is overloading LM Studio. There are two active `update-opportunity-scores` processes, one dry run and one non-dry run, both with `--concurrency 3`. Logs show repeated `429 Too Many Requests`.

## Current Flow

### Daily Crawl

Entry point: `src/crawler/run_daily.py`

1. Parse `--limit`, `--date`, and `--skip-llm`.
2. Build `CloudflareClient`, optional `LMStudioClient`, and Supabase repositories.
3. Call `CrawlOrchestrator.run(run_date=crawl_date)`.
4. Fetch countries from Cloudflare unless injected by tests.
5. For each country and each ranking type in `TRENDING_RISE`, `TRENDING_STEADY`:
   - Fetch Radar ranking entries.
   - Normalize each returned domain.
   - Upsert domain if new.
   - Insert or upsert an observation.
   - For new domains only, optionally run LLM enrichment.
   - For new enriched domains, compute deterministic observation score and upsert observation again.
6. Mark the crawl as completed, partial, or failed.
7. Intended: run opportunity scoring for new domains.

### Deterministic Trend Scoring

Module: `src/domains/scoring.py`

This is the original observation score. It uses:

- base score
- ranking type bonus
- rank tier bonus
- percentage rank change bonus
- multi-country bonus
- LLM category bonus or penalty
- novelty bonus
- LLM idea-potential bonus
- known giant penalty
- reviewed penalty

This code is well covered by tests, but some components are not actually wired into the crawler:

- `countries_seen_today` is never passed, so multi-country bonus stays at zero.
- `review_status` is not passed, so reviewed penalty is not used in the crawl.
- `initial_score` and `latest_best_score` are not updated when observation scores are computed.

### LLM Opportunity Scoring

Entry points:

- `main.py update-opportunity-scores`
- `start update-opportunity-scores`
- `run_scoring.sh`

The command:

1. Reads domains from Supabase ordered by `latest_best_score`.
2. Filters by `opportunity_score IS NULL` when `--only-missing` is used.
3. Loads all observations for each domain.
4. Computes `trend_score` as max observation score.
5. Optionally fetches homepage content.
6. Calls the LLM with a Romanian-market opportunity prompt.
7. Applies a known-global-giant score cap.
8. Updates opportunity fields on `domains`.

This is directionally aligned with `docs/Update_scoring.md`, but the current implementation needs stronger throttling, structured output enforcement, and clearer failure state handling.

## Findings

### 1. Crawler completion breaks when new domains are found

Location: `src/crawler/orchestrator.py:249`

`run()` calls:

```python
await self._run_opportunity_scoring(counters["new_domains"])
```

But `_run_opportunity_scoring` is defined at `src/crawler/orchestrator.py:254` inside `run()` after `return run`, so it is unreachable and not a class method.

Observed verification:

```text
.venv/bin/python -m pytest -q
2 failed, 142 passed
```

Failure:

```text
AttributeError: 'CrawlOrchestrator' object has no attribute '_run_opportunity_scoring'
```

Impact: a successful crawl with new domains can mark the run complete and then crash the process.

Recommended fix: move `_run_opportunity_scoring()` to class scope or remove the automatic post-crawl scoring hook and keep scoring strictly as a separate command. `docs/Update_scoring.md` explicitly recommended keeping opportunity scoring separate from daily crawl, so removing the hook is probably cleaner.

### 2. `--date` is only partially honored

Locations:

- `src/crawler/run_daily.py:44`
- `src/crawler/orchestrator.py:79`
- `src/crawler/progress.py:19`
- `src/db/repositories.py:184`
- `src/cloudflare/radar_service.py:54`

`run_daily.py` parses a crawl date and passes it to the orchestrator. The orchestrator uses it as `observed_date`, but run creation/resume uses `get_today_run()` and `create_run()` without the requested date. Cloudflare requests also do not pass a `date` query parameter.

Impact:

- Running `--date 2026-05-15` can create or resume a run for the machine's current date.
- The database `crawl_runs.run_date` can disagree with `domain_observations.observed_date`.
- The Cloudflare API fetches whatever its default date is, not necessarily the requested date.

Recommended fix: thread `run_date` through `get_or_create_today_run()`, `get_today_run()`, and `create_run()`. Add optional `date` support to `RadarService.get_top_domains()` only after re-checking Cloudflare docs and updating `docs/API_CONTRACTS.md`.

### 3. Docs say sequential crawl, code runs countries concurrently

Locations:

- `docs/DECISIONS.md` ADR-020
- `src/crawler/orchestrator.py:40`
- `src/crawler/orchestrator.py:121`
- `src/crawler/orchestrator.py:210`

ADR-020 says countries are processed sequentially. Code launches one task per country and gates only `_process_country()` with a semaphore. Default `CRAWL_CONCURRENCY` is 8.

Impact:

- Cloudflare request rate is higher than documented.
- LLM enrichment can run concurrently across countries.
- Country statuses can be marked `running` before the semaphore is acquired.
- The `.crawl_stop` graceful-stop behavior no longer means "after current country"; many country tasks are already queued.

Recommended fix: choose one architecture and update the docs. Given the current LM Studio pressure, sequential country processing or low explicit concurrency is safer.

### 4. Async bulk-writer docs are not reflected in the hot path

Locations:

- `docs/Architecture.md`
- `src/crawler/orchestrator.py:17`
- `src/domains/dedupe.py:76`
- `src/db/repositories.py:20`

The architecture doc says domains and observations are collected in memory and written in batches of 800. In the active crawler path, `dedupe_and_insert()` still calls synchronous repository methods per domain and per observation.

There are also unused bulk helpers. One helper posts observations to `/rest/v1/observations`, but the table is `domain_observations`.

Impact:

- Expected crawl performance gains may not exist.
- Documentation overstates the implementation.
- If the unused bulk path is wired later, observation writes will target the wrong endpoint.

Recommended fix: either implement the documented buffered bulk path end to end or revert the architecture doc to match the current per-record write path.

### 5. Observation upsert is done twice for new enriched domains

Locations:

- `src/domains/dedupe.py:76`
- `src/crawler/orchestrator.py:370`
- `src/db/repositories.py:151`

`dedupe_and_insert()` inserts the observation immediately. For new domains with LLM enrichment, the orchestrator upserts the same observation again with `observation_score`.

The second upsert does not pass `categories` or `raw_payload`, so it can overwrite useful Cloudflare debug data with empty values.

Impact:

- Extra write load.
- Risk of losing observation metadata for newly scored domains.

Recommended fix: split dedupe from observation persistence, or have `dedupe_and_insert()` accept the final score and all final fields once. A smaller fix is to preserve `categories` and `raw_payload` on the second upsert.

### 6. Deterministic score is not fully operational

Locations:

- `src/domains/scoring.py`
- `src/crawler/orchestrator.py:360`
- `src/db/repositories.py:47`

The scoring function supports multi-country, reviewed-status, novelty, category, and potential components, but the crawler only applies it for new domains after LLM enrichment.

Issues:

- Existing domains get new observations without refreshed observation scores.
- Multi-country bonus is never calculated from actual same-day country count.
- `initial_score` stays `NULL` because the domain row is inserted before the score exists.
- `latest_best_score` is not maintained.

Impact: dashboard sorting can depend on SQL fallback scores or stale/null domain scores instead of the canonical deterministic score.

Recommended fix: calculate a trend score for every observation, then aggregate separately. If multi-country is required, do a second scoring pass after all observations for the day are inserted.

### 7. Opportunity scoring overloads LM Studio

Locations:

- `src/opportunity/update_opportunity_scores.py:389`
- `src/opportunity/scorer.py:59`
- `src/llm/lmstudio_client.py:98`
- `logs/scoring_20260518_233220.log`

The latest log shows many `HTTP/1.1 429 Too Many Requests` responses from LM Studio. There are also two active scoring processes:

```text
main.py update-opportunity-scores --fetch-homepage --only-missing --concurrency 3 --model meta/llama-3.1-8b-instruct --dry-run
main.py update-opportunity-scores --fetch-homepage --only-missing --concurrency 3 --model meta/llama-3.1-8b-instruct
```

Retries are layered:

- `LMStudioClient._post()` retries HTTP errors.
- `OpportunityScorer.score_domain()` retries the whole LLM call again.

Impact: one scored domain can generate many repeated requests during a local rate-limit event, making recovery slower.

Recommended fix: use one retry layer, lower default scoring concurrency to 1, and optionally add a process lock file so two scoring jobs cannot run concurrently unless explicitly allowed.

### 8. Opportunity scoring does not use structured output

Locations:

- `src/llm/lmstudio_client.py:35`
- `src/opportunity/scorer.py:66`
- `src/opportunity/schemas.py`
- `logs/scoring_20260518_233220.log`

LLM enrichment uses `response_format: json_schema`, but opportunity scoring uses `LMStudioClient.call()`, which sends no schema. Logs show validation failures where the LLM returns `None` for required string fields.

Impact: preventable retries and failed scores.

Recommended fix: add a schema-aware call path for `OpportunityScoreResult` or let `OpportunityScorer` build its own `response_format: json_schema` payload.

### 9. Failed opportunity scores are retried forever by `--only-missing`

Location: `src/opportunity/update_opportunity_scores.py:290`

On failure, the code updates `opportunity_breakdown` and LLM metadata, but does not set `opportunity_score`.

Impact: `--only-missing` selects the same failed rows again and again.

Recommended fix: add an explicit `opportunity_score_status` column, or set a sentinel score with error metadata. Status is cleaner.

### 10. Homepage-fetch behavior changed away from the spec

Locations:

- `docs/Update_scoring.md`
- `src/opportunity/update_opportunity_scores.py:235`
- `src/opportunity/prompt.py:122`
- `scoring_final.log`
- `logs/scoring_20260518_233220.log`

Earlier logs show "Skipping LLM scoring" when homepage fetch returned no content. Current code logs "scoring without homepage" and calls the LLM anyway.

The prompt says that if `homepage_excerpt` is `None` and the model does not recognize the domain with certainty, it must return confidence 1 and score 0.

Impact: many LLM calls are spent on low-context domains that should either be skipped or scored from already stored enrichment context.

Recommended fix: decide the policy:

- strict anti-hallucination: skip LLM when homepage and existing enrichment are both missing;
- context-first: allow scoring without homepage when existing `llm_summary` and observations are strong enough.

Then encode it in tests and docs.

### 11. UTC timestamp rule is not consistently enforced

Locations:

- `src/domains/dedupe.py:56`
- `src/db/repositories.py:47`
- `src/db/repositories.py:87`
- `src/db/repositories.py:214`
- `src/opportunity/update_opportunity_scores.py:268`

The app uses `datetime.now()` and `datetime.utcnow().isoformat()` in multiple places. The project rule says timestamps should be stored in UTC and converted to Europe/Bucharest only for display.

Impact: naive timestamps can be interpreted incorrectly depending on client, server, and database behavior.

Recommended fix: use timezone-aware UTC timestamps, for example `datetime.now(timezone.utc).isoformat()`.

### 12. Supabase run uniqueness conflicts with "create a new run"

Locations:

- `supabase/schemas/001_core.sql`
- `src/crawler/progress.py:31`
- `logs/app.log`

`crawl_runs.run_date` is unique. `get_or_create_today_run()` says completed/failed runs should create a new run, but that violates the unique constraint for the same date. Historical logs show duplicate-key failures for `crawl_runs_run_date_key`.

Recommended fix: either:

- enforce one crawl run per date and reuse/reset it, or
- remove the unique constraint and make resume lookup select the latest run for the requested date.

## What Is Working

- Domain normalization uses `tldextract`, which is the right approach for public suffix handling.
- `domains` plus `domain_observations` is the right data model.
- The uniqueness constraint on `(domain_id, observed_date, country_code, ranking_type)` correctly prevents duplicate observation rows.
- LLM enrichment is correctly skipped for already-known normalized domains.
- The deterministic scoring function itself is simple, explainable, and well tested.
- The opportunity scoring command exists and writes the expected columns from `004_opportunity_scores.sql`.
- The dashboard RPC has been extended to filter and sort by opportunity score fields.

## Test Status

Command:

```bash
.venv/bin/python -m pytest -q
```

Result:

```text
2 failed, 142 passed
```

Failures:

- `tests/test_crawler.py::test_orchestrator_runs_with_mocked_repos` confirms the `_run_opportunity_scoring` class-method bug.
- `tests/test_data_loader.py::test_load_collected_data_calls_range_rpc` is stale. The implementation now passes opportunity filter params to the RPC, but the test expects the old argument set.

Plain `pytest -q` outside `.venv` also fails collection because the global Python does not have `bs4` installed. The venv is the correct environment for this repo.

## Recommended Fix Order

1. Stop duplicate scoring jobs before continuing long scoring runs. LM Studio is currently rate-limiting.
2. Decide whether opportunity scoring should stay separate from the crawler. If yes, remove the post-crawl `_run_opportunity_scoring` hook. If no, move it to class scope and test it.
3. Fix `--date` semantics across crawl run lookup, run creation, and Cloudflare ranking query. Update `docs/API_CONTRACTS.md` only after verifying Cloudflare docs.
4. Make crawler concurrency match the chosen architecture and update ADR-020.
5. Fix observation scoring persistence so one observation write preserves score, categories, and raw payload.
6. Make opportunity scoring schema-based and reduce retry pressure.
7. Add an explicit opportunity scoring failure status so `--only-missing` does not loop on permanent failures.
8. Replace naive timestamps with timezone-aware UTC.
9. Update tests for the chosen behavior.

## Notes

No API tokens were copied into this report.

No Cloudflare code was changed during this analysis, so official Cloudflare docs were not fetched or re-verified.
