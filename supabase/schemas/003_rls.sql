-- 003_rls.sql
-- Row Level Security policies for all tables

-- Enable RLS on all tables
ALTER TABLE domains ENABLE ROW LEVEL SECURITY;
ALTER TABLE domain_observations ENABLE ROW LEVEL SECURITY;
ALTER TABLE crawl_runs ENABLE ROW LEVEL SECURITY;
ALTER TABLE crawl_country_status ENABLE ROW LEVEL SECURITY;
ALTER TABLE domain_comments ENABLE ROW LEVEL SECURITY;

-- For an internal tool, we allow full access with the service role key.
-- These policies are placeholders — adjust based on your auth strategy.

-- Domains: allow all operations (internal tool, no public access)
CREATE POLICY "domains_full_access"
    ON domains
    FOR ALL
    USING (true)
    WITH CHECK (true);

-- Domain observations: allow all operations
CREATE POLICY "domain_observations_full_access"
    ON domain_observations
    FOR ALL
    USING (true)
    WITH CHECK (true);

-- Crawl runs: allow all operations
CREATE POLICY "crawl_runs_full_access"
    ON crawl_runs
    FOR ALL
    USING (true)
    WITH CHECK (true);

-- Crawl country status: allow all operations
CREATE POLICY "crawl_country_status_full_access"
    ON crawl_country_status
    FOR ALL
    USING (true)
    WITH CHECK (true);

-- Domain comments: allow all operations
CREATE POLICY "domain_comments_full_access"
    ON domain_comments
    FOR ALL
    USING (true)
    WITH CHECK (true);
