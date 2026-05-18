import asyncio
import os
from collections.abc import Callable
from datetime import date
from pathlib import Path

from src.cloudflare.client import CloudflareClient
from src.cloudflare.radar_service import RadarService
from src.config.constants import CrawlRunStatus, RankingType
from src.crawler.progress import get_or_create_today_run
from src.db.repositories import (
    CrawlCountryStatusRepository,
    CrawlRunRepository,
    DomainRepository,
    ObservationRepository,
)
from src.db.repositories import bulk_upsert_domains, bulk_insert_observations
from src.domains.dedupe import dedupe_and_insert
from src.domains.scoring import score_observation
from src.llm.lmstudio_client import LMStudioClient
from src.utils.logging import get_logger
from src.db.async_client import post, get

logger = get_logger(__name__)

async def load_existing_domains() -> dict[str, str]:
    """Load all existing domains from Supabase.

    Returns a mapping ``normalized_domain -> id`` for quick in‑memory lookups.
    """
    # Use GET with select query parameters to fetch existing domains.
    rows = await get('/rest/v1/domains', params={'select': 'id,normalized_domain'})
    return {row['normalized_domain']: row['id'] for row in rows}

# File used to signal graceful stop of crawling process
STOP_FILE = Path('.crawl_stop')

RANKING_TYPES = [RankingType.TRENDING_RISE, RankingType.TRENDING_STEADY]

CONCURRENCY = int(os.environ.get("CRAWL_CONCURRENCY", "8"))



class CrawlOrchestrator:
    def __init__(
        self,
        cloudflare_client: CloudflareClient | None = None,
        llm_client: LMStudioClient | None = None,
        domain_repo: DomainRepository | None = None,
        observation_repo: ObservationRepository | None = None,
        crawl_run_repo: CrawlRunRepository | None = None,
        country_status_repo: CrawlCountryStatusRepository | None = None,
        limit_per_country: int = 100,
        on_domain_discovered: Callable | None = None,
    ):
        self._radar = RadarService(cloudflare_client)
        self._llm = llm_client
        self._domain_repo = domain_repo
        self._observation_repo = observation_repo
        self._crawl_run_repo = crawl_run_repo
        self._country_status_repo = country_status_repo
        self._limit = limit_per_country
        self._on_domain_discovered = on_domain_discovered

    async def run(
        self,
        run_date: date | None = None,
        countries: list[dict] | None = None,
    ) -> dict:
        """Execute the full daily crawl pipeline.

        Args:
            run_date: Date for the crawl run (defaults to today).
            countries: Pre-fetched country list. If None, fetches from Cloudflare.

        Returns:
            Final crawl_run dict.
        """
        today = run_date or date.today()
        logger.info(f"Starting daily crawl for {today}")
        # Load existing domains into an in‑memory cache for fast deduplication
        existing_domains = await load_existing_domains()
        self._existing_domains = existing_domains

        run = get_or_create_today_run(self._crawl_run_repo, self._country_status_repo)
        run_id = run["id"]
        is_resume = run.get("resume", False)

        if countries is None:
            countries = await self._radar.get_geolocations()

        if is_resume:
            existing_statuses = self._country_status_repo.get_country_statuses_for_run(run_id)
            done_countries = {s["country_code"] for s in existing_statuses if s.get("status") in ("completed", "failed")}

            new_domains = run.get("new_domains_count", 0)
            duplicate_domains = run.get("duplicate_domains_count", 0)
            llm_processed = run.get("llm_processed_count", 0)
            llm_skipped = run.get("llm_skipped_count", 0)
            requests_total = run.get("requests_total", 0)
            requests_failed = run.get("requests_failed", 0)
            countries_completed = run.get("countries_completed", 0)
            countries_failed = run.get("countries_failed", 0)

            logger.info(f"Resuming run {run_id}: {len(done_countries)} countries already processed")
        else:
            done_countries = set()

            new_domains = 0
            duplicate_domains = 0
            llm_processed = 0
            llm_skipped = 0
            requests_total = 0
            requests_failed = 0
            countries_completed = 0
            countries_failed = 0

        countries_total = len(countries)
        self._crawl_run_repo.update_progress(run_id, countries_total=countries_total)

        semaphore = asyncio.Semaphore(CONCURRENCY)
        lock = asyncio.Lock()
        stopped = False

        # Counters shared across concurrent tasks
        counters = {
            "new_domains": new_domains,
            "duplicate_domains": duplicate_domains,
            "llm_processed": llm_processed,
            "llm_skipped": llm_skipped,
            "requests_total": requests_total,
            "requests_failed": requests_failed,
            "countries_completed": countries_completed,
            "countries_failed": countries_failed,
        }

        async def _run_country(country: dict) -> None:
            nonlocal stopped
            country_code = country["code"]
            country_name = country["name"]

            if country_code in done_countries:
                return

            if STOP_FILE.exists():
                async with lock:
                    stopped = True
                return

            self._country_status_repo.upsert_country_status(
                crawl_run_id=run_id,
                country_code=country_code,
                country_name=country_name,
                status="running",
            )

            async with semaphore:
                try:
                    country_new, country_dup, country_llm, country_skip, country_req = await self._process_country(
                        run_id=run_id,
                        country_code=country_code,
                        country_name=country_name,
                        observed_date=today,
                    )

                    async with lock:
                        counters["new_domains"] += country_new
                        counters["duplicate_domains"] += country_dup
                        counters["llm_processed"] += country_llm
                        counters["llm_skipped"] += country_skip
                        counters["requests_total"] += country_req
                        counters["countries_completed"] += 1

                    self._country_status_repo.upsert_country_status(
                        crawl_run_id=run_id,
                        country_code=country_code,
                        country_name=country_name,
                        status="completed",
                        items_found=country_new + country_dup,
                        new_domains=country_new,
                        duplicate_domains=country_dup,
                    )

                except Exception as exc:
                    logger.error(f"Failed to process {country_code}: {exc}")
                    async with lock:
                        counters["countries_failed"] += 1
                        counters["requests_failed"] += len(RANKING_TYPES)

                    self._country_status_repo.upsert_country_status(
                        crawl_run_id=run_id,
                        country_code=country_code,
                        country_name=country_name,
                        status="failed",
                        error_message=str(exc),
                    )

            self._crawl_run_repo.update_progress(
                run_id=run_id,
                countries_completed=counters["countries_completed"],
                countries_failed=counters["countries_failed"],
                requests_total=counters["requests_total"],
                requests_failed=counters["requests_failed"],
                new_domains_count=counters["new_domains"],
                duplicate_domains_count=counters["duplicate_domains"],
                llm_processed_count=counters["llm_processed"],
                llm_skipped_count=counters["llm_skipped"],
            )

        await asyncio.gather(*[_run_country(c) for c in countries])

        if stopped:
            STOP_FILE.unlink(missing_ok=True)
            self._crawl_run_repo.update_progress(
                run_id=run_id,
                countries_completed=counters["countries_completed"],
                countries_failed=counters["countries_failed"],
                requests_total=counters["requests_total"],
                requests_failed=counters["requests_failed"],
                new_domains_count=counters["new_domains"],
                duplicate_domains_count=counters["duplicate_domains"],
                llm_processed_count=counters["llm_processed"],
                llm_skipped_count=counters["llm_skipped"],
            )
            run = self._crawl_run_repo.complete_run(run_id, status=CrawlRunStatus.PARTIAL)
            logger.info(
                f"Crawl {run_id} paused: {counters['countries_completed']}/{countries_total} countries, "
                f"{counters['new_domains']} new, {counters['duplicate_domains']} dupes"
            )
            return run

        countries_failed = counters["countries_failed"]
        countries_completed = counters["countries_completed"]

        if countries_failed > 0 and countries_completed > 0:
            final_status = CrawlRunStatus.PARTIAL
        elif countries_completed == 0:
            final_status = CrawlRunStatus.FAILED
        else:
            final_status = CrawlRunStatus.COMPLETED

        run = self._crawl_run_repo.complete_run(run_id, status=final_status)
        logger.info(
            f"Crawl {run_id} finished: {final_status} "
            f"({countries_completed}/{countries_total} countries, "
            f"{counters['new_domains']} new, {counters['duplicate_domains']} dupes)"
        )

        if counters["new_domains"] > 0 and final_status in (CrawlRunStatus.COMPLETED, CrawlRunStatus.PARTIAL):
            await self._run_opportunity_scoring(counters["new_domains"])

        return run

        async def _run_opportunity_scoring(self, new_domains_count: int) -> None:
            """Score new domains with the opportunity LLM after crawl completes.

            Uses the exact command the user expects:
            .venv/bin/python main.py update-opportunity-scores \
                --fetch-homepage \
                --only-missing \
                --concurrency 3 \
                --model 'meta/llama-3.1-8b-instruct'
            """
            try:
                from src.opportunity.update_opportunity_scores import update_opportunity_scores

                logger.info(f"Running opportunity scoring for {new_domains_count} new domains with LLM model meta/llama-3.1-8b-instruct...")
                scored = await update_opportunity_scores(
                    only_missing=True,
                    limit=new_domains_count,
                    dry_run=False,
                    fetch_homepage=True,
                    concurrency=3,
                    model='meta/llama-3.1-8b-instruct',
                )
                logger.info(f"Opportunity scoring complete: {scored} domains scored")
            except Exception as e:
                logger.error(f"Opportunity scoring failed after crawl: {e}")

    async def _process_country(
        self,
        run_id: str,
        country_code: str,
        country_name: str,
        observed_date: date,
    ) -> tuple[int, int, int, int, int]:
        """Process a single country for all ranking types.

        Returns:
            (new_domains, duplicates, llm_processed, llm_skipped, requests_made)
        """
        new_domains = 0
        duplicate_domains = 0
        llm_processed = 0
        llm_skipped = 0
        requests_made = 0

        for ranking_type in RANKING_TYPES:
            entries = await self._radar.get_top_domains(
                location=country_code,
                ranking_type=ranking_type,
                limit=self._limit,
            )
            requests_made += 1

            for entry in entries:
                try:
                    result = dedupe_and_insert(
                        domain_repo=self._domain_repo,
                        observation_repo=self._observation_repo,
                        raw_domain=entry.domain,
                        crawl_run_id=run_id,
                        observed_date=observed_date,
                        country_code=country_code,
                        country_name=country_name,
                        ranking_type=ranking_type.value.lower().replace("_", "_"),
                        rank=entry.rank,
                        pct_rank_change=entry.pct_rank_change,
                        categories=[
                            {"id": c.id, "name": c.name, "superCategoryId": c.super_category_id} for c in entry.categories
                        ],
                        raw_payload={
                            "domain": entry.domain,
                            "rank": entry.rank,
                            "pctRankChange": entry.pct_rank_change,
                        },
                        existing_domains=self._existing_domains,
                    )
                except ValueError as exc:
                    logger.warning(f"Skipping unparseable domain '{entry.domain}' for {country_code}: {exc}")
                    continue

                if result.is_new:
                    new_domains += 1

                    if self._llm:
                        llm_result = await self._llm.enrich(
                            domain=result.normalized_domain,
                            categories=[
                                {"id": c.id, "name": c.name}
                                for c in entry.categories
                            ],
                            country_code=country_code,
                            ranking_type=ranking_type.value,
                            rank=entry.rank,
                            pct_rank_change=entry.pct_rank_change,
                        )

                        self._domain_repo.update_llm_fields(
                            domain_id=result.domain_id,
                            summary=llm_result.summary,
                            category=llm_result.category,
                            business_model=llm_result.business_model,
                            target_users=llm_result.target_users,
                            localization_angle=llm_result.localization_angle,
                            risk_notes=llm_result.risk_notes,
                        )
                        llm_processed += 1

                        scoring = score_observation(
                            ranking_type=ranking_type.value,
                            rank=entry.rank,
                            pct_rank_change=entry.pct_rank_change,
                            llm_category=llm_result.category,
                            llm_idea_potential=llm_result.idea_potential,
                            first_seen_date=observed_date,
                            normalized_domain=result.normalized_domain,
                        )

                        self._observation_repo.insert_observation(
                            domain_id=result.domain_id,
                            crawl_run_id=run_id,
                            observed_date=observed_date,
                            country_code=country_code,
                            country_name=country_name,
                            ranking_type=ranking_type.value.lower(),
                            rank=entry.rank,
                            pct_rank_change=entry.pct_rank_change,
                            observation_score=scoring.total,
                        )
                    else:
                        llm_skipped += 1
                else:
                    duplicate_domains += 1
                    llm_skipped += 1

                if self._on_domain_discovered:
                    self._on_domain_discovered(result)

        return new_domains, duplicate_domains, llm_processed, llm_skipped, requests_made
