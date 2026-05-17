# TrendingFounder

Discover trending domains globally via Cloudflare Radar, deduplicate them, enrich with a local LLM, and triage in a fast mobile-friendly Streamlit dashboard.

## Prerequisites

- Python >= 3.14
- [uv](https://docs.astral.sh/uv/) or pip
- Supabase account (free tier is enough for MVP)
- [LM Studio](https://lmstudio.ai/) running locally (for LLM enrichment)
- Cloudflare API token with Radar read access

## Quick Start

```bash
# 1. Clone and enter the repo
git clone <repo-url>
cd TrendingFounder

# 2. Create a virtual environment and install dependencies
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"

# 3. Copy env template and fill in your values
cp .env.example .env

# 4. Start LM Studio locally (for LLM enrichment phase)

# 5. Run the daily crawl (Phase 2+)
python -m src.crawler.run_daily

# 6. Launch the Streamlit dashboard (Phase 7+)
./start trending
```

## Project Structure

```
TrendingFounder/
  app/
    streamlit_app.py    # Primary dashboard: Collected Data + Reports
    data_loader.py      # Supabase view loaders for Streamlit
    components/         # Domain cards, filters, metrics, comments UI
    pages/              # Legacy/reference Streamlit pages
  src/
    config/             # Settings and constants
    cloudflare/         # Cloudflare Radar API client and schemas
    domains/            # Normalization, deduplication, scoring
    llm/                # LM Studio client, prompts, schemas
    db/                 # Supabase client, repositories, queries
    crawler/            # Daily crawl orchestration and progress tracking
    utils/              # Logging helpers
  supabase/             # SQL schemas and migrations
  tests/                # pytest test suite
  docs/                 # Project documentation
```

## Documentation

| File | Purpose |
|---|---|
| [docs/PLAN.md](docs/PLAN.md) | Full product plan, architecture, data model |
| [docs/AGENTS.md](docs/AGENTS.md) | Rules for AI coding agents |
| [docs/TASKS.md](docs/TASKS.md) | Phase-by-phase task checklist |
| [docs/DECISIONS.md](docs/DECISIONS.md) | Architecture decision records (ADRs) |
| [docs/API_CONTRACTS.md](docs/API_CONTRACTS.md) | Cloudflare API endpoint contracts |
| [docs/CHANGELOG.md](docs/CHANGELOG.md) | Release history |
| [docs/RUNBOOK.md](docs/RUNBOOK.md) | Operational runbook |
| [docs/PROMPTS.md](docs/PROMPTS.md) | Full project spec for AI tools (schema, scoring, flow) |

## MVP Phases

| Phase | Name | Status |
|---|---|---|
| 1 | Foundation (skeleton, settings, logging) | Complete |
| 2 | Cloudflare ingestion | Complete |
| 3 | Supabase schema | Complete |
| 4 | Deduplication | Complete |
| 5 | LLM enrichment | Complete |
| 6 | Scoring engine | Complete |
| 7 | Streamlit UI | Complete |
| 8 | Hardening | Complete |

## License

MIT
