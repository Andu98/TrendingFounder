-- 005_github_opencode.sql
-- Separate GitHub topic discovery tables for the opencode repository feed.

CREATE TABLE IF NOT EXISTS github_repo_crawl_runs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    started_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    finished_at TIMESTAMPTZ,
    status TEXT NOT NULL DEFAULT 'running' CHECK (status IN ('running', 'completed', 'failed')),
    source_url TEXT NOT NULL,
    topic TEXT NOT NULL DEFAULT 'opencode',
    target_limit INTEGER NOT NULL DEFAULT 500,
    fetched_count INTEGER NOT NULL DEFAULT 0,
    new_count INTEGER NOT NULL DEFAULT 0,
    baseline_count INTEGER NOT NULL DEFAULT 0,
    error TEXT
);

CREATE TABLE IF NOT EXISTS github_repositories (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    github_repo_id BIGINT UNIQUE NOT NULL,
    full_name TEXT UNIQUE NOT NULL,
    owner TEXT NOT NULL,
    repo_name TEXT NOT NULL,
    html_url TEXT NOT NULL,
    description TEXT,
    language TEXT,
    stargazers_count INTEGER NOT NULL DEFAULT 0,
    forks_count INTEGER NOT NULL DEFAULT 0,
    open_issues_count INTEGER NOT NULL DEFAULT 0,
    pushed_at TIMESTAMPTZ,
    updated_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ,
    first_seen_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    last_seen_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    first_seen_run_id UUID REFERENCES github_repo_crawl_runs(id),
    is_baseline BOOLEAN NOT NULL DEFAULT FALSE,
    is_new BOOLEAN NOT NULL DEFAULT TRUE,
    review_status TEXT NOT NULL DEFAULT 'pending' CHECK (
        review_status IN ('pending', 'interesting', 'ignored', 'built', 'not_relevant')
    ),
    notes TEXT
);

CREATE TABLE IF NOT EXISTS github_repo_observations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    run_id UUID REFERENCES github_repo_crawl_runs(id),
    repository_id UUID REFERENCES github_repositories(id),
    observed_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    rank INTEGER NOT NULL,
    stars INTEGER NOT NULL,
    forks INTEGER NOT NULL,
    open_issues INTEGER NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_github_repositories_full_name
    ON github_repositories(full_name);

CREATE INDEX IF NOT EXISTS idx_github_repositories_github_repo_id
    ON github_repositories(github_repo_id);

CREATE INDEX IF NOT EXISTS idx_github_repositories_new_baseline_first_seen
    ON github_repositories(is_new, is_baseline, first_seen_at);

CREATE INDEX IF NOT EXISTS idx_github_repo_observations_run_id
    ON github_repo_observations(run_id);

CREATE INDEX IF NOT EXISTS idx_github_repo_observations_repository_id
    ON github_repo_observations(repository_id);

ALTER TABLE github_repo_crawl_runs ENABLE ROW LEVEL SECURITY;
ALTER TABLE github_repositories ENABLE ROW LEVEL SECURITY;
ALTER TABLE github_repo_observations ENABLE ROW LEVEL SECURITY;

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_policies
        WHERE schemaname = 'public'
          AND tablename = 'github_repo_crawl_runs'
          AND policyname = 'github_repo_crawl_runs_full_access'
    ) THEN
        CREATE POLICY "github_repo_crawl_runs_full_access"
            ON github_repo_crawl_runs
            FOR ALL
            USING (true)
            WITH CHECK (true);
    END IF;

    IF NOT EXISTS (
        SELECT 1 FROM pg_policies
        WHERE schemaname = 'public'
          AND tablename = 'github_repositories'
          AND policyname = 'github_repositories_full_access'
    ) THEN
        CREATE POLICY "github_repositories_full_access"
            ON github_repositories
            FOR ALL
            USING (true)
            WITH CHECK (true);
    END IF;

    IF NOT EXISTS (
        SELECT 1 FROM pg_policies
        WHERE schemaname = 'public'
          AND tablename = 'github_repo_observations'
          AND policyname = 'github_repo_observations_full_access'
    ) THEN
        CREATE POLICY "github_repo_observations_full_access"
            ON github_repo_observations
            FOR ALL
            USING (true)
            WITH CHECK (true);
    END IF;
END $$;
