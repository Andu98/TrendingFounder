# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Common Development Commands

- **Install dependencies (dev)**: `pip install -e "[dev]"` (or `uv pip install -e "[dev]"`).
- **Run the full CLI entrypoint**: `./start` (provided by the `src.cli:start` console script).
- **Run the crawl**: `python -m src.crawler.run_daily` or `./start crawler`.
- **Score opportunities**: `./start-score` (runs `src.cli:start` with scoring args).
- **Launch the Streamlit UI**: `./start trending` (executes `app/streamlit_app.py`).
- **Run a single test**: `pytest tests/<path_to_test>.py -k <test_name>`.
- **Run the entire test suite**: `pytest` (configured via `pyproject.toml`).
- **Lint / format**: `ruff .` and `black .` (available in dev dependencies).

## High‑Level Architecture

- **Entry point** (`src/cli.py`): defines the `start` console script that wires together crawl, scoring, and UI commands.
- **Crawler** (`src/crawler/`): orchestrates daily domain collection from Cloudflare Radar, tracks progress, and stores raw results.
- **Domain processing** (`src/domains/`): deduplication, normalization, and scoring logic for each discovered domain.
- **LLM enrichment** (`src/llm/`): client for an OpenAI‑compatible endpoint, prompts, and response schemas used to enrich domain data.
- **Supabase integration** (`src/db/` & `supabase/` schemas): async client, repository pattern, and SQL migrations for persisting enriched data.
- **Streamlit dashboard** (`app/`): UI layer that loads data via the Supabase view loader (`app/data_loader.py`) and presents it through reusable components (`app/components/`).
- **Configuration** (`src/config/`): central settings (environment variables, defaults) accessed throughout the codebase.
- **Utilities** (`src/utils/`): logging helper and misc shared functions.

## Important Documentation

- **README.md**: high‑level overview, prerequisites, and quick‑start commands.
- **docs/PLAN.md**: detailed product plan, architecture decisions, and data model.
- **docs/AGENTS.md**: rules for AI coding agents used by the project.
- **docs/DECISIONS.md**: architecture decision records (ADRs).
- **docs/RUNBOOK.md**: operational runbook for production deployments.
- **docs/diagrams/**: SVG diagrams referenced in the README for system overview, external services, crawl pipeline, and scoring algorithm.

When a future Claude instance works in this repository, it can consult this file for the common commands and the overall structure without needing to read every individual module.
