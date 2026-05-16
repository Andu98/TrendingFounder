-- 001_core.sql
-- Core tables for TrendingFounder

-- Enable UUID extension
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Domains: one row per unique normalized domain
CREATE TABLE IF NOT EXISTS domains (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    normalized_domain TEXT NOT NULL UNIQUE,
    display_url TEXT,
    first_seen_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    first_seen_date DATE NOT NULL DEFAULT CURRENT_DATE,
    first_country_code TEXT,
    first_country_name TEXT,
    first_ranking_type TEXT,
    llm_summary TEXT,
    llm_category TEXT,
    llm_business_model TEXT,
    llm_target_users TEXT,
    llm_localization_angle TEXT,
    llm_risk_notes TEXT,
    initial_score NUMERIC,
    latest_best_score NUMERIC,
    review_status TEXT NOT NULL DEFAULT 'pending' CHECK (review_status IN ('pending', 'ok', 'exists', 'bad')),
    reviewed_at TIMESTAMPTZ,
    reviewed_by TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_domains_normalized_domain ON domains (normalized_domain);
CREATE INDEX IF NOT EXISTS idx_domains_review_status ON domains (review_status);
CREATE INDEX IF NOT EXISTS idx_domains_first_seen_date ON domains (first_seen_date);

-- Crawl runs: tracks each daily crawl execution
CREATE TABLE IF NOT EXISTS crawl_runs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    run_date DATE NOT NULL UNIQUE DEFAULT CURRENT_DATE,
    status TEXT NOT NULL DEFAULT 'pending' CHECK (status IN ('pending', 'running', 'completed', 'failed', 'partial')),
    started_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    finished_at TIMESTAMPTZ,
    countries_total INTEGER NOT NULL DEFAULT 0,
    countries_completed INTEGER NOT NULL DEFAULT 0,
    countries_failed INTEGER NOT NULL DEFAULT 0,
    requests_total INTEGER NOT NULL DEFAULT 0,
    requests_failed INTEGER NOT NULL DEFAULT 0,
    new_domains_count INTEGER NOT NULL DEFAULT 0,
    duplicate_domains_count INTEGER NOT NULL DEFAULT 0,
    llm_processed_count INTEGER NOT NULL DEFAULT 0,
    llm_skipped_count INTEGER NOT NULL DEFAULT 0,
    error_message TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_crawl_runs_run_date ON crawl_runs (run_date);
CREATE INDEX IF NOT EXISTS idx_crawl_runs_status ON crawl_runs (status);

-- Domain observations: one row per appearance in a country/day/ranking type
CREATE TABLE IF NOT EXISTS domain_observations (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    domain_id UUID NOT NULL REFERENCES domains(id) ON DELETE CASCADE,
    crawl_run_id UUID REFERENCES crawl_runs(id) ON DELETE SET NULL,
    observed_date DATE NOT NULL DEFAULT CURRENT_DATE,
    observed_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    country_code TEXT NOT NULL,
    country_name TEXT NOT NULL,
    ranking_type TEXT NOT NULL CHECK (ranking_type IN ('popular', 'trending_rise', 'trending_steady')),
    rank INTEGER NOT NULL,
    pct_rank_change NUMERIC,
    categories JSONB DEFAULT '[]'::jsonb,
    observation_score NUMERIC,
    raw_payload JSONB,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (domain_id, observed_date, country_code, ranking_type)
);

CREATE INDEX IF NOT EXISTS idx_observations_domain_id ON domain_observations (domain_id);
CREATE INDEX IF NOT EXISTS idx_observations_crawl_run_id ON domain_observations (crawl_run_id);
CREATE INDEX IF NOT EXISTS idx_observations_observed_date ON domain_observations (observed_date);
CREATE INDEX IF NOT EXISTS idx_observations_country_code ON domain_observations (country_code);
CREATE INDEX IF NOT EXISTS idx_observations_ranking_type ON domain_observations (ranking_type);

-- Crawl country status: granular progress per country per run
CREATE TABLE IF NOT EXISTS crawl_country_status (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    crawl_run_id UUID NOT NULL REFERENCES crawl_runs(id) ON DELETE CASCADE,
    country_code TEXT NOT NULL,
    country_name TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'pending' CHECK (status IN ('pending', 'running', 'completed', 'failed')),
    started_at TIMESTAMPTZ,
    finished_at TIMESTAMPTZ,
    error_message TEXT,
    items_found INTEGER NOT NULL DEFAULT 0,
    new_domains INTEGER NOT NULL DEFAULT 0,
    duplicate_domains INTEGER NOT NULL DEFAULT 0,
    UNIQUE (crawl_run_id, country_code)
);

CREATE INDEX IF NOT EXISTS idx_crawl_country_status_crawl_run_id ON crawl_country_status (crawl_run_id);
CREATE INDEX IF NOT EXISTS idx_crawl_country_status_status ON crawl_country_status (status);

-- Domain comments: user notes per domain
CREATE TABLE IF NOT EXISTS domain_comments (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    domain_id UUID NOT NULL REFERENCES domains(id) ON DELETE CASCADE,
    author_name TEXT NOT NULL,
    message TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_domain_comments_domain_id ON domain_comments (domain_id);
CREATE INDEX IF NOT EXISTS idx_domain_comments_created_at ON domain_comments (created_at);
