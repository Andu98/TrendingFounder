-- 004_opportunity_scores.sql
-- Add LLM-based Romanian market opportunity scoring columns to domains table

ALTER TABLE domains
    ADD COLUMN IF NOT EXISTS opportunity_score NUMERIC,
    ADD COLUMN IF NOT EXISTS opportunity_breakdown JSONB,
    ADD COLUMN IF NOT EXISTS opportunity_summary TEXT,
    ADD COLUMN IF NOT EXISTS opportunity_idea TEXT,
    ADD COLUMN IF NOT EXISTS opportunity_category TEXT,
    ADD COLUMN IF NOT EXISTS opportunity_type TEXT,
    ADD COLUMN IF NOT EXISTS opportunity_confidence INTEGER,
    ADD COLUMN IF NOT EXISTS trend_score NUMERIC,
    ADD COLUMN IF NOT EXISTS opportunity_score_status TEXT CHECK (
        opportunity_score_status IS NULL OR opportunity_score_status IN ('scored', 'failed')
    ),
    ADD COLUMN IF NOT EXISTS opportunity_score_error TEXT,
    ADD COLUMN IF NOT EXISTS llm_opportunity_model TEXT,
    ADD COLUMN IF NOT EXISTS llm_opportunity_prompt_version TEXT,
    ADD COLUMN IF NOT EXISTS llm_opportunity_updated_at TIMESTAMPTZ;
