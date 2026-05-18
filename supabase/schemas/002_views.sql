-- 002_views.sql
-- Dashboard views for Today, This Week, and Stats

-- Today view: best score today across all countries
CREATE OR REPLACE VIEW v_domains_today AS
SELECT
    dom.id,
    dom.normalized_domain,
    dom.display_url,
    dom.first_seen_date,
    dom.llm_summary,
    dom.llm_category,
    dom.llm_business_model,
    dom.review_status,
    dom.initial_score,
    dom.latest_best_score,
    dom.opportunity_score,
    dom.opportunity_category,
    dom.opportunity_type,
    dom.opportunity_confidence,
    dom.trend_score,
    MAX(obs.observation_score) AS best_score_today,
    COUNT(DISTINCT obs.country_code) AS countries_today,
    COUNT(DISTINCT obs.ranking_type) AS ranking_types_count,
    ARRAY_AGG(DISTINCT obs.country_code) AS country_codes,
    ARRAY_AGG(DISTINCT obs.ranking_type) AS ranking_types,
    (SELECT COUNT(*) FROM domain_comments c WHERE c.domain_id = dom.id) AS comment_count
FROM domains dom
JOIN domain_observations obs ON obs.domain_id = dom.id
WHERE obs.observed_date = CURRENT_DATE
GROUP BY dom.id, dom.normalized_domain, dom.display_url, dom.first_seen_date,
    dom.llm_summary, dom.llm_category, dom.llm_business_model,
    dom.review_status, dom.initial_score, dom.latest_best_score,
    dom.opportunity_score, dom.opportunity_category, dom.opportunity_type,
    dom.opportunity_confidence, dom.trend_score;

-- This week view: best score in last 7 days
CREATE OR REPLACE VIEW v_domains_this_week AS
SELECT
    dom.id, dom.normalized_domain, dom.display_url, dom.first_seen_date,
    dom.llm_summary, dom.llm_category, dom.llm_business_model,
    dom.review_status, dom.initial_score, dom.latest_best_score,
    dom.opportunity_score, dom.opportunity_category, dom.opportunity_type,
    dom.opportunity_confidence, dom.trend_score,
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
    dom.review_status, dom.initial_score, dom.latest_best_score,
    dom.opportunity_score, dom.opportunity_category, dom.opportunity_type,
    dom.opportunity_confidence, dom.trend_score;

-- Date range RPC: filtered, aggregated, sorted, and paginated in the database
CREATE OR REPLACE FUNCTION get_domains_for_range(
    start_date DATE DEFAULT CURRENT_DATE,
    end_date DATE DEFAULT CURRENT_DATE,
    show_reviewed BOOLEAN DEFAULT FALSE,
    status_filter TEXT DEFAULT 'All Statuses',
    category_filter TEXT DEFAULT 'All Categories',
    search_query TEXT DEFAULT '',
    sort_by TEXT DEFAULT 'Score High → Low',
    page INTEGER DEFAULT 1,
    page_size INTEGER DEFAULT 50,
    min_opportunity_score INTEGER DEFAULT 0,
    min_opportunity_confidence INTEGER DEFAULT 0,
    opportunity_type_filter TEXT DEFAULT 'All Types',
    hide_global_giants BOOLEAN DEFAULT FALSE
)
RETURNS TABLE (
    id UUID,
    normalized_domain TEXT,
    display_url TEXT,
    first_seen_date DATE,
    llm_summary TEXT,
    llm_category TEXT,
    llm_business_model TEXT,
    review_status TEXT,
    initial_score NUMERIC,
    latest_best_score NUMERIC,
    best_score_today NUMERIC,
    countries_today BIGINT,
    ranking_types_count BIGINT,
    country_codes TEXT[],
    ranking_types TEXT[],
    first_seen_in_range DATE,
    last_seen_in_range DATE,
    times_observed BIGINT,
    comment_count BIGINT,
    total_count BIGINT,
    opportunity_score NUMERIC,
    opportunity_category TEXT,
    opportunity_type TEXT,
    opportunity_confidence INTEGER,
    trend_score NUMERIC
)
LANGUAGE sql
STABLE
AS $$
WITH params AS (
    SELECT
        LEAST(COALESCE($1, CURRENT_DATE), COALESCE($2, COALESCE($1, CURRENT_DATE))) AS date_start,
        GREATEST(COALESCE($1, CURRENT_DATE), COALESCE($2, COALESCE($1, CURRENT_DATE))) AS date_end,
        COALESCE($3, FALSE) AS show_reviewed,
        NULLIF(TRIM($4), '') AS status_filter,
        NULLIF(TRIM($5), '') AS category_filter,
        NULLIF(TRIM($6), '') AS search_query,
        COALESCE(NULLIF(TRIM($7), ''), 'Score High → Low') AS sort_label,
        GREATEST(COALESCE($8, 1), 1) AS page_number,
        GREATEST(COALESCE($9, 50), 1) AS rows_per_page,
        COALESCE($10, 0) AS min_opp_score,
        COALESCE($11, 0) AS min_opp_confidence,
        NULLIF(TRIM($12), '') AS opp_type_filter,
        COALESCE($13, FALSE) AS hide_giants
),
aggregated AS (
    SELECT
        dom.id,
        dom.normalized_domain,
        dom.display_url,
        dom.first_seen_at,
        dom.first_seen_date,
        dom.llm_summary,
        dom.llm_category,
        dom.llm_business_model,
        dom.review_status,
        dom.initial_score,
        dom.latest_best_score,
        dom.opportunity_score,
        dom.opportunity_category,
        dom.opportunity_type,
        dom.opportunity_confidence,
        dom.trend_score,
        COALESCE(
            MAX(obs.observation_score),
            MAX(
                CASE obs.ranking_type
                    WHEN 'trending_rise' THEN 80
                    WHEN 'trending_steady' THEN 65
                    WHEN 'popular' THEN 45
                    ELSE 20
                END
                + CASE
                    WHEN obs.rank <= 10 THEN 25
                    WHEN obs.rank <= 25 THEN 18
                    WHEN obs.rank <= 50 THEN 12
                    WHEN obs.rank <= 100 THEN 6
                    ELSE 0
                END
                + CASE
                    WHEN obs.pct_rank_change IS NULL THEN 0
                    ELSE LEAST(GREATEST(obs.pct_rank_change, 0), 100) / 5
                END
            ),
            dom.latest_best_score,
            dom.initial_score,
            0
        ) AS best_score_today,
        COUNT(DISTINCT obs.country_code) AS countries_today,
        COUNT(DISTINCT obs.ranking_type) AS ranking_types_count,
        (ARRAY_AGG(DISTINCT obs.country_code ORDER BY obs.country_code)
            FILTER (WHERE obs.country_code IS NOT NULL))::TEXT[] AS country_codes,
        (ARRAY_AGG(DISTINCT obs.ranking_type ORDER BY obs.ranking_type)
            FILTER (WHERE obs.ranking_type IS NOT NULL))::TEXT[] AS ranking_types,
        MIN(obs.observed_date) AS first_seen_in_range,
        MAX(obs.observed_date) AS last_seen_in_range,
        COUNT(*) AS times_observed,
        (SELECT COUNT(*) FROM domain_comments c WHERE c.domain_id = dom.id) AS comment_count
    FROM params p
    JOIN domain_observations obs
        ON obs.observed_date BETWEEN p.date_start AND p.date_end
    JOIN domains dom ON dom.id = obs.domain_id
    WHERE
        CASE
            WHEN p.status_filter = '__none__'
                THEN FALSE
            WHEN p.status_filter IS NOT NULL AND p.status_filter <> 'All Statuses'
                THEN dom.review_status = ANY(
                    ARRAY(
                        SELECT TRIM(status_value)
                        FROM UNNEST(STRING_TO_ARRAY(p.status_filter, ',')) AS statuses(status_value)
                        WHERE TRIM(status_value) IN ('pending', 'ok', 'exists', 'bad')
                    )
                )
            WHEN NOT p.show_reviewed
                THEN dom.review_status = 'pending'
            ELSE TRUE
        END
        AND (
            p.category_filter IS NULL
            OR p.category_filter = 'All Categories'
            OR COALESCE(NULLIF(dom.llm_category, ''), 'Other') = p.category_filter
        )
        AND (
            p.search_query IS NULL
            OR dom.normalized_domain ILIKE '%' || p.search_query || '%'
            OR COALESCE(dom.display_url, '') ILIKE '%' || p.search_query || '%'
        )
        AND (
            p.min_opp_score = 0
            OR COALESCE(dom.opportunity_score, 0) >= p.min_opp_score
        )
        AND (
            p.min_opp_confidence = 0
            OR COALESCE(dom.opportunity_confidence, 0) >= p.min_opp_confidence
        )
        AND (
            p.opp_type_filter IS NULL
            OR p.opp_type_filter = 'All Types'
            OR COALESCE(dom.opportunity_type, '') = p.opp_type_filter
        )
        AND (
            NOT p.hide_giants
            OR LOWER(dom.normalized_domain) NOT IN (
                'amazon.com', 'udemy.com', 'box.com', 'google.com', 'youtube.com',
                'facebook.com', 'instagram.com', 'netflix.com', 'booking.com', 'airbnb.com',
                'microsoft.com', 'apple.com', 'temu.com', 'aliexpress.com', 'wikipedia.org',
                'linkedin.com', 'x.com', 'twitter.com', 'tiktok.com',
                'github.com', 'stackoverflow.com', 'zoom.us', 'slack.com', 'whatsapp.com',
                'reddit.com', 'pinterest.com', 'spotify.com', 'twitch.tv', 'discord.com',
                'notion.so', 'canva.com', 'figma.com', 'adobe.com', 'salesforce.com',
                'oracle.com', 'ibm.com', 'intel.com', 'nvidia.com', 'tesla.com'
            )
        )
    GROUP BY dom.id, dom.normalized_domain, dom.display_url, dom.first_seen_at, dom.first_seen_date,
        dom.llm_summary, dom.llm_category, dom.llm_business_model,
        dom.review_status, dom.initial_score, dom.latest_best_score,
        dom.opportunity_score, dom.opportunity_category, dom.opportunity_type,
        dom.opportunity_confidence, dom.trend_score
),
counted AS (
    SELECT aggregated.*, COUNT(*) OVER() AS total_count
    FROM aggregated
)
SELECT
    counted.id,
    counted.normalized_domain,
    counted.display_url,
    counted.first_seen_date,
    counted.llm_summary,
    counted.llm_category,
    counted.llm_business_model,
    counted.review_status,
    counted.initial_score,
    counted.latest_best_score,
    counted.best_score_today,
    counted.countries_today,
    counted.ranking_types_count,
    counted.country_codes,
    counted.ranking_types,
    counted.first_seen_in_range,
    counted.last_seen_in_range,
    counted.times_observed,
    counted.comment_count,
    counted.total_count,
    counted.opportunity_score,
    counted.opportunity_category,
    counted.opportunity_type,
    counted.opportunity_confidence,
    counted.trend_score
FROM counted
CROSS JOIN params p
ORDER BY
    CASE WHEN p.sort_label = 'Opportunity Score' THEN counted.opportunity_score END DESC NULLS LAST,
    CASE WHEN p.sort_label IN ('Score High → Low', 'Score (desc)') THEN counted.best_score_today END DESC NULLS LAST,
    CASE WHEN p.sort_label IN ('Score Low → High', 'Score (asc)') THEN counted.best_score_today END ASC NULLS LAST,
    CASE WHEN p.sort_label = 'Newest' THEN counted.first_seen_at END DESC NULLS LAST,
    CASE WHEN p.sort_label IN ('Country Count', 'Country count') THEN counted.countries_today END DESC NULLS LAST,
    counted.best_score_today DESC NULLS LAST,
    counted.normalized_domain ASC
LIMIT (SELECT rows_per_page FROM params)
OFFSET (SELECT (page_number - 1) * rows_per_page FROM params);
$$;

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
