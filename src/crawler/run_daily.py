"""Daily crawl entry point.

Usage:
    python -m src.crawler.run_daily
    python -m src.crawler.run_daily --limit 50
    python -m src.crawler.run_daily --date 2026-05-15
"""

import argparse
import asyncio
import sys
from datetime import date

from src.cloudflare.client import CloudflareClient
from src.crawler.orchestrator import CrawlOrchestrator
from src.db.repositories import (
    CrawlCountryStatusRepository,
    CrawlRunRepository,
    DomainRepository,
    ObservationRepository,
)
from src.llm.lmstudio_client import LMStudioClient
from src.utils.logging import get_logger, setup_logging


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run the daily domain crawl.")
    parser.add_argument(
        "--limit",
        type=int,
        default=100,
        help="Number of domains to fetch per country per ranking type.",
    )
    parser.add_argument(
        "--date",
        type=str,
        default=None,
        help="Crawl date in YYYY-MM-DD format (defaults to today).",
    )
    parser.add_argument(
        "--skip-llm",
        action="store_true",
        help="Skip LLM enrichment for new domains.",
    )
    return parser.parse_args()


async def main():
    setup_logging()
    args = parse_args()

    logger = get_logger(__name__)
    logger.info("TrendingFounder daily crawl starting...")

    crawl_date = date.fromisoformat(args.date) if args.date else date.today()

    cf_client = CloudflareClient()
    llm_client = None if args.skip_llm else LMStudioClient()

    domain_repo = DomainRepository()
    observation_repo = ObservationRepository()
    crawl_run_repo = CrawlRunRepository()
    country_status_repo = CrawlCountryStatusRepository()

    orchestrator = CrawlOrchestrator(
        cloudflare_client=cf_client,
        llm_client=llm_client,
        domain_repo=domain_repo,
        observation_repo=observation_repo,
        crawl_run_repo=crawl_run_repo,
        country_status_repo=country_status_repo,
        limit_per_country=args.limit,
    )

    try:
        result = await orchestrator.run(run_date=crawl_date)
        logger.info(f"Crawl completed: {result.get('status')}")
    except Exception as exc:
        logger.error(f"Crawl failed: {exc}")
        sys.exit(1)
    finally:
        await cf_client.close()
        if llm_client is not None:
            await llm_client.close()


if __name__ == "__main__":
    asyncio.run(main())
