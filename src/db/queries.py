"""Named SQL queries for views used by the dashboard."""

V_DOMAINS_TODAY = """
SELECT * FROM v_domains_today
WHERE review_status = %(review_status)s
ORDER BY best_score_today DESC
LIMIT %(limit)s
"""

V_DOMAINS_THIS_WEEK = """
SELECT * FROM v_domains_this_week
WHERE review_status = %(review_status)s
ORDER BY best_score_week DESC
LIMIT %(limit)s
"""

V_CRAWL_STATS = """
SELECT * FROM v_crawl_stats
WHERE run_date = %(run_date)s
"""

V_CRAWL_COUNTRY_PROGRESS = """
SELECT * FROM v_crawl_country_progress
WHERE run_date = %(run_date)s
ORDER BY country_code
"""
