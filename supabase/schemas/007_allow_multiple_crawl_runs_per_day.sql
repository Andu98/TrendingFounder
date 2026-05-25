-- 007_allow_multiple_crawl_runs_per_day.sql
-- Allow repeated scheduled domain crawler executions on the same calendar date.

ALTER TABLE IF EXISTS crawl_runs
    DROP CONSTRAINT IF EXISTS crawl_runs_run_date_key;

CREATE INDEX IF NOT EXISTS idx_crawl_runs_run_date_started_at
    ON crawl_runs (run_date, started_at DESC);
