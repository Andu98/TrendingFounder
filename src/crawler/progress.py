"""Crawl progress tracking utilities."""

from src.db.repositories import CrawlCountryStatusRepository, CrawlRunRepository
from src.utils.logging import get_logger

logger = get_logger(__name__)


def get_or_create_today_run(
    crawl_run_repo: CrawlRunRepository,
    country_status_repo: CrawlCountryStatusRepository,
) -> dict:
    """Get today's existing crawl run or create a new one.

    If a run exists and is in 'running' or 'partial' state, it can be resumed.
    If it's 'completed' or 'failed', a new run is created.

    Returns:
        The crawl_run dict with a 'resume' flag indicating if this is a resume.
    """
    existing = crawl_run_repo.get_today_run()

    if existing and existing["status"] in ("running", "partial"):
        logger.info(f"Resuming existing crawl run {existing['id']} " f"(status={existing['status']})")
        existing["resume"] = True
        return existing

    if existing:
        logger.info(f"Today already has a {existing['status']} run. " f"Creating a new run.")

    run = crawl_run_repo.create_run()
    run["resume"] = False
    return run


def get_completed_countries(
    country_status_repo: CrawlCountryStatusRepository,
    crawl_run_id: str,
) -> set[str]:
    """Get the set of country codes already completed or failed in this run."""
    statuses = country_status_repo.get_country_statuses_for_run(crawl_run_id)
    return {s["country_code"] for s in statuses if s.get("status") in ("completed", "failed")}


def format_progress(run: dict) -> str:
    """Format crawl progress as a human-readable string."""
    total = run.get("countries_total", 0)
    completed = run.get("countries_completed", 0)
    failed = run.get("countries_failed", 0)
    status = run.get("status", "unknown")

    if total == 0:
        return f"Status: {status} (no countries queued)"

    pct = completed / total * 100
    return f"Status: {status} | " f"{completed}/{total} countries ({pct:.0f}%) | " f"{failed} failed"
