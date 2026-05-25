-- 008_latest_crawl_run_views.sql
-- Keep reporting views focused on the latest crawl run when a date has multiple executions.

CREATE OR REPLACE VIEW v_crawl_stats AS
WITH latest_runs AS (
    SELECT DISTINCT ON (run_date) *
    FROM crawl_runs
    ORDER BY run_date DESC, started_at DESC
)
SELECT
    runs.run_date, runs.status AS crawl_status,
    runs.countries_total, runs.countries_completed, runs.countries_failed,
    runs.requests_total, runs.requests_failed,
    runs.new_domains_count, runs.duplicate_domains_count,
    runs.llm_processed_count, runs.llm_skipped_count,
    runs.started_at, runs.finished_at,
    (
        SELECT COUNT(*)
        FROM domains d
        WHERE d.first_seen_date = CURRENT_DATE
    ) AS new_domains_today,
    (
        SELECT COUNT(*)
        FROM domain_observations obs
        WHERE obs.observed_date = CURRENT_DATE
    ) AS observations_today,
    (
        SELECT COUNT(*)
        FROM domains d
        WHERE d.review_status != 'pending'
          AND d.reviewed_at >= CURRENT_DATE
    ) AS reviewed_today,
    (
        SELECT COUNT(*)
        FROM domains d
        WHERE d.review_status != 'pending'
    ) AS reviewed_total,
    (
        SELECT COUNT(*)
        FROM v_domains_today v
        WHERE v.best_score_today > 80
    ) AS high_score_today
FROM latest_runs runs;

CREATE OR REPLACE VIEW v_crawl_country_progress AS
WITH latest_run AS (
    SELECT *
    FROM crawl_runs
    WHERE run_date = CURRENT_DATE
    ORDER BY started_at DESC
    LIMIT 1
)
SELECT
    runs.id AS crawl_run_id, runs.run_date, runs.status AS crawl_status,
    ccs.country_code, ccs.country_name, ccs.status AS country_status,
    ccs.started_at, ccs.finished_at, ccs.error_message,
    ccs.items_found, ccs.new_domains, ccs.duplicate_domains
FROM latest_run runs
LEFT JOIN crawl_country_status ccs ON ccs.crawl_run_id = runs.id
ORDER BY ccs.country_code;
