-- 002_views.sql
-- Dashboard views for Today, This Week, and Stats

-- Today view: best score today across all countries
CREATE OR REPLACE VIEW v_domains_today AS
SELECT
    d.id,
    d.normalized_domain,
    d.display_url,
    d.first_seen_date,
    d.llm_summary,
    d.llm_category,
    d.llm_business_model,
    d.review_status,
    d.initial_score,
    d.latest_best_score,
    MAX(do.observation_score) AS best_score_today,
    COUNT(DISTINCT do.country_code) AS countries_today,
    COUNT(DISTINCT do.ranking_type) AS ranking_types_count,
    ARRAY_AGG(DISTINCT do.country_code) AS country_codes,
    ARRAY_AGG(DISTINCT do.ranking_type) AS ranking_types,
    (SELECT COUNT(*) FROM domain_comments c WHERE c.domain_id = d.id) AS comment_count
FROM domains dom
JOIN domain_observations obs ON obs.domain_id = dom.id
WHERE obs.observed_date = CURRENT_DATE
GROUP BY dom.id, dom.normalized_domain, dom.display_url, dom.first_seen_date,
    dom.llm_summary, dom.llm_category, dom.llm_business_model,
    dom.review_status, dom.initial_score, dom.latest_best_score;

-- This week view: best score in last 7 days
CREATE OR REPLACE VIEW v_domains_this_week AS
SELECT
    dom.id, dom.normalized_domain, dom.display_url, dom.first_seen_date,
    dom.llm_summary, dom.llm_category, dom.llm_business_model,
    dom.review_status, dom.initial_score, dom.latest_best_score,
    MAX(obs.observation_score) AS best_score_week,
    COUNT(DISTINCT obs.country_code) AS countries_this_week,
    COUNT(DISTINCT obs.ranking_type) AS ranking_types_count,
    ARRAY_AGG(DISTINCT obs.country_code) AS country_codes,
    ARRAY_AGG(DISTINCT obs.ranking_type) AS ranking_types,
    MIN(obs.observed_date) AS first_seen_in_week,
    MAX(obs.observed_date) AS last_seen_in_week,
    COUNT(*) AS times_observed,
    (SELECT COUNT(*) FROM domain_comments c WHERE c.domain_id = dom.id) AS comment_count
FROM domains dom
JOIN domain_observations obs ON obs.domain_id = dom.id
WHERE obs.observed_date >= CURRENT_DATE - INTERVAL '7 days'
GROUP BY dom.id, dom.normalized_domain, dom.display_url, dom.first_seen_date,
    dom.llm_summary, dom.llm_category, dom.llm_business_model,
    dom.review_status, dom.initial_score, dom.latest_best_score;

-- Stats view: aggregated metrics for the dashboard
CREATE OR REPLACE VIEW v_crawl_stats AS
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
FROM crawl_runs runs;

-- Country-level status for today's crawl
CREATE OR REPLACE VIEW v_crawl_country_progress AS
SELECT
    runs.id AS crawl_run_id, runs.run_date, runs.status AS crawl_status,
    ccs.country_code, ccs.country_name, ccs.status AS country_status,
    ccs.started_at, ccs.finished_at, ccs.error_message,
    ccs.items_found, ccs.new_domains, ccs.duplicate_domains
FROM crawl_runs runs
LEFT JOIN crawl_country_status ccs ON ccs.crawl_run_id = runs.id
WHERE runs.run_date = CURRENT_DATE
ORDER BY ccs.country_code;
