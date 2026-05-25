from pathlib import Path


def test_crawl_runs_run_date_allows_multiple_runs_per_day():
    core_schema = Path("supabase/schemas/001_core.sql").read_text()
    migration = Path("supabase/schemas/007_allow_multiple_crawl_runs_per_day.sql").read_text()

    assert "run_date DATE NOT NULL UNIQUE" not in core_schema
    assert "DROP CONSTRAINT IF EXISTS crawl_runs_run_date_key" in migration
    assert "idx_crawl_runs_run_date_started_at" in core_schema


def test_crawl_reporting_views_use_latest_run_for_date():
    views_schema = Path("supabase/schemas/002_views.sql").read_text()
    migration = Path("supabase/schemas/008_latest_crawl_run_views.sql").read_text()

    assert "SELECT DISTINCT ON (run_date) *" in views_schema
    assert "FROM latest_runs runs" in views_schema
    assert "WITH latest_run AS" in views_schema
    assert "CREATE OR REPLACE VIEW v_crawl_country_progress" in migration
