"""Main command for updating opportunity scores using LLM."""

import argparse
import asyncio
import logging
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import httpx
try:
    from bs4 import BeautifulSoup
except ImportError:  # pragma: no cover
    import re
    class _SimpleTag:
        def __init__(self, text: str):
            self._text = text
        def get_text(self) -> str:
            return self._text.strip()
        def get(self, attr: str, default: str = "") -> str:
            return default
    class BeautifulSoup:  # type: ignore
        def __init__(self, html: str, parser: str = "html.parser"):
            self._html = html
        def find(self, name: str, attrs: dict | None = None):
            if name == "title":
                m = re.search(r"<title>(.*?)</title>", self._html, re.IGNORECASE | re.DOTALL)
                return _SimpleTag(m.group(1)) if m else None
            if name == "meta" and attrs and attrs.get("name") == "description":
                tag_match = re.search(r'<meta[^>]*name=["\']description["\'][^>]*>', self._html, re.IGNORECASE | re.DOTALL)
                if tag_match:
                    content_match = re.search(r'content=["\']([^"\']+)["\']', tag_match.group(0), re.IGNORECASE)
                    if content_match:
                        class _MetaTag:
                            def __init__(self, content):
                                self._content = content
                            def get(self, attr, default=None):
                                return self._content if attr == "content" else default
                            def get_text(self):
                                return ""
                        return _MetaTag(content_match.group(1))
                return None
            return None
        def find_all(self, names):
            results = []
            for name in names:
                pattern = rf"<{name}[^>]*>(.*?)</{name}>"
                for m in re.finditer(pattern, self._html, re.IGNORECASE | re.DOTALL):
                    results.append(_SimpleTag(m.group(1)))
            return results


from src.config.settings import Settings
from src.db.repositories import DomainRepository, ObservationRepository
from src.opportunity.constants import KNOWN_GLOBAL_GIANTS
from src.opportunity.scorer import OpportunityScorer

logger = logging.getLogger(__name__)

STATUS_UPDATE_COLUMNS = {"opportunity_score_status", "opportunity_score_error"}
PROGRESS_LOG_INTERVAL = 25


def utc_now_iso() -> str:
    return datetime.now(UTC).isoformat()


def _setup_logging() -> logging.FileHandler:
    """Configure logging to both console and a timestamped file in logs/."""
    logs_dir = Path("logs")
    logs_dir.mkdir(exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_file = logs_dir / f"scoring_{timestamp}.log"

    handler = logging.FileHandler(log_file, encoding="utf-8")
    handler.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] %(name)s: %(message)s"))

    root = logging.getLogger()
    root.setLevel(logging.INFO)
    root.addHandler(handler)

    console = logging.StreamHandler()
    console.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] %(name)s: %(message)s"))
    root.addHandler(console)

    return handler


def _increment(stats: dict[str, int] | None, key: str, amount: int = 1) -> None:
    if stats is not None:
        stats[key] = stats.get(key, 0) + amount


def _is_missing_status_column_error(exc: Exception) -> bool:
    message = str(exc)
    return any(column in message for column in STATUS_UPDATE_COLUMNS)


def _update_opportunity_fields(domain_repo: DomainRepository, domain_id: str, update: dict) -> dict:
    try:
        return domain_repo.update_opportunity_fields(domain_id, update)
    except Exception as exc:
        if STATUS_UPDATE_COLUMNS.intersection(update) and _is_missing_status_column_error(exc):
            fallback_update = {k: v for k, v in update.items() if k not in STATUS_UPDATE_COLUMNS}
            logger.warning(
                "Supabase opportunity status columns are not available yet. "
                "Apply supabase/schemas/004_opportunity_scores.sql to persist scoring status."
            )
            return domain_repo.update_opportunity_fields(domain_id, fallback_update)
        raise


def is_known_global_giant(domain: str) -> bool:
    """Check if a domain is in the known global giants set."""
    return domain.lower() in KNOWN_GLOBAL_GIANTS


def apply_giant_cap(domain: str, score: int) -> int:
    """Apply the global giant cap if needed."""
    if is_known_global_giant(domain) and score > 20:
        return 20
    return score


async def fetch_homepage_excerpt(url: str) -> str | None:
    """
    Fetch and extract key information from a domain's homepage.

    Args:
        url: The URL to fetch

    Returns:
        Extracted content or None if failed
    """
    try:
        # If BeautifulSoup is unavailable, skip extraction and return None
        if BeautifulSoup is None:
            logger.warning("BeautifulSoup not available; cannot extract homepage excerpt.")
            return None
        headers = {
            "User-Agent": (
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
                "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
            ),
            "Accept": (
                "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8"
            ),
            "Accept-Language": "en-US,en;q=0.9",
        }
        async with httpx.AsyncClient(timeout=5.0, follow_redirects=True, headers=headers) as client:
            response = await client.get(url)
            response.raise_for_status()

            soup = BeautifulSoup(response.text, "html.parser")

            # Extract key information
            title = soup.find("title")
            meta_desc = soup.find("meta", attrs={"name": "description"})
            headings = soup.find_all(["h1", "h2"])
            first_p = soup.find("p")

            # Build excerpt
            excerpt_parts = []

            if title:
                excerpt_parts.append(f"Title: {title.get_text().strip()}")

            if meta_desc:
                excerpt_parts.append(f"Description: {meta_desc.get('content', '').strip()}")

            if headings:
                heading_texts = [h.get_text().strip() for h in headings[:3]]  # First 3 headings
                excerpt_parts.append(f"Headings: {'; '.join(heading_texts)}")

            if first_p:
                text = first_p.get_text().strip()
                if len(text) > 20:
                    excerpt_parts.append(f"Content: {text[:200]}...")

            return "\n".join(excerpt_parts) if excerpt_parts else None

    except Exception as e:
        logger.warning(f"Failed to fetch homepage for {url}: {e}")
        return None


async def compute_trend_score(observations: list[dict]) -> float:
    """
    Compute the trend score from observations.

    Args:
        observations: List of observation dictionaries

    Returns:
        Maximum observation score (representing current trend strength)
    """
    if not observations:
        return 0.0

    scores = [obs.get("observation_score") for obs in observations]
    valid_scores = [s for s in scores if s is not None]

    if not valid_scores:
        return 0.0

    return max(valid_scores)


async def get_domain_context(
    domain_repo: DomainRepository,
    observation_repo: ObservationRepository,
    domain_id: str,
    domain: str,
    display_url: str,
    review_status: str,
    existing_llm_summary: str | None,
    existing_llm_category: str | None,
    existing_llm_potential: int | None,
    first_seen_at: str,
) -> dict[str, Any]:
    """
    Get all context needed for opportunity scoring.

    Args:
        domain_repo: Domain repository instance
        observation_repo: Observation repository instance
        domain_id: Domain ID
        domain: Domain name
        display_url: Display URL
        review_status: Review status
        existing_llm_summary: Existing LLM summary
        existing_llm_category: Existing LLM category
        existing_llm_potential: Existing LLM potential score
        first_seen_at: When the domain was first seen

    Returns:
        Dictionary with all context information
    """
    # Get recent observations (last 7 days)
    # In a real implementation, we'd filter by date, but for now we'll get all
    # This approach may need to be adjusted in the future
    try:
        observations_result = (
            observation_repo._client.table("domain_observations").select("*").eq("domain_id", domain_id).execute()
        )
        observations = observations_result.data or []
    except Exception as e:
        logger.warning(f"Failed to fetch observations for {domain}: {e}")
        observations = []

    # Compute trend score from observations
    trend_score = await compute_trend_score(observations)

    # Extract distinct countries, ranking types, etc.
    countries_observed = list(set(obs.get("country_code") for obs in observations if obs.get("country_code")))
    ranking_types = list(set(obs.get("ranking_type") for obs in observations if obs.get("ranking_type")))

    # Get best rank and max pct_rank_change
    best_rank = min(obs.get("rank", float("inf")) for obs in observations) if observations else 0
    pct_rank_change = max(obs.get("pct_rank_change", 0) for obs in observations) if observations else None

    # Check for Romanian signals
    romanian_signals = any(obs.get("country_code") == "RO" for obs in observations)

    return {
        "domain": domain,
        "display_url": display_url,
        "trend_score": trend_score,
        "countries_observed": countries_observed,
        "ranking_types": ranking_types,
        "best_rank": best_rank,
        "pct_rank_change": pct_rank_change,
        "first_seen_at": first_seen_at,
        "existing_category": existing_llm_category,
        "existing_summary": existing_llm_summary,
        "existing_llm_potential": existing_llm_potential,
        "review_status": review_status,
        "romanian_signals": romanian_signals,
    }


async def score_single_domain(
    domain_repo: DomainRepository,
    observation_repo: ObservationRepository,
    scorer: OpportunityScorer,
    domain_row: dict,
    fetch_homepage: bool,
    dry_run: bool,
    stats: dict[str, int] | None = None,
) -> dict[str, Any]:
    """
    Score a single domain.

    Args:
        domain_repo: Domain repository instance
        observation_repo: Observation repository instance
        scorer: Opportunity scorer instance
        domain_row: Domain database row
        fetch_homepage: Whether to fetch homepage content
        dry_run: Whether this is a dry run

    Returns:
        Dictionary with scoring results
    """
    domain_id = domain_row["id"]
    domain = domain_row["normalized_domain"]
    display_url = domain_row["display_url"]
    review_status = domain_row.get("review_status", "pending")
    existing_llm_summary = domain_row.get("llm_summary")
    existing_llm_category = domain_row.get("llm_category")
    existing_llm_potential = domain_row.get("llm_potential")
    first_seen_at = domain_row.get("first_seen_at", "")

    # Get context
    context = await get_domain_context(
        domain_repo,
        observation_repo,
        domain_id,
        domain,
        display_url,
        review_status,
        existing_llm_summary,
        existing_llm_category,
        existing_llm_potential,
        first_seen_at,
    )

    # Optionally fetch homepage
    homepage_excerpt = None
    if fetch_homepage and not dry_run:
        try:
            homepage_excerpt = await fetch_homepage_excerpt(display_url)
            if homepage_excerpt is None:
                _increment(stats, "homepage_misses")
                logger.warning(f"Homepage crawl returned no content for {domain}, scoring without homepage.")
        except Exception as e:
            _increment(stats, "homepage_misses")
            logger.warning(f"Failed to fetch homepage for {domain}: {e}")

    # Score with LLM
    try:
        result = await scorer.score_domain(context, homepage_excerpt)

        # Apply guardrails
        final_score = apply_giant_cap(domain, result.opportunity_score)

        # Prepare update dictionary
        update = {
            "opportunity_score": final_score,
            "opportunity_breakdown": result.model_dump(),
            "opportunity_summary": result.one_sentence_summary,
            "opportunity_idea": result.romania_adaptation_idea,
            "opportunity_category": result.recommended_category,
            "opportunity_type": result.opportunity_type,
            "opportunity_confidence": result.confidence,
            "trend_score": context["trend_score"],
            "llm_opportunity_model": scorer.model,
            "llm_opportunity_prompt_version": "romania_llm_score_v1",
            "llm_opportunity_updated_at": utc_now_iso(),
            "opportunity_score_status": "scored",
            "opportunity_score_error": None,
        }

        if not dry_run:
            _update_opportunity_fields(domain_repo, domain_id, update)

        return {"success": True, "domain": domain, "score": final_score, "update": update, "error": None}

    except Exception as e:
        logger.error(f"Failed to score domain {domain}: {e}")

        # For failed scoring, preserve existing score if present, or set to 0
        update = {
            "opportunity_breakdown": {"error": str(type(e).__name__), "message": str(e)},
            "llm_opportunity_model": scorer.model,
            "llm_opportunity_prompt_version": "romania_llm_score_v1",
            "llm_opportunity_updated_at": utc_now_iso(),
            "opportunity_score_status": "failed",
            "opportunity_score_error": str(e)[:500],
        }

        if not dry_run:
            _update_opportunity_fields(domain_repo, domain_id, update)

        return {"success": False, "domain": domain, "score": None, "update": update, "error": str(e)}


async def update_opportunity_scores(
    only_missing: bool = False,
    limit: int | None = None,
    min_trend_score: float | None = None,
    dry_run: bool = False,
    force: bool = False,
    fetch_homepage: bool = False,
    concurrency: int = 5,
    llm_concurrency: int = 1,
    model: str | None = None,
) -> int:
    """
    Update opportunity scores for domains.

    Args:
        only_missing: Only score domains without existing scores
        limit: Maximum number of domains to process
        min_trend_score: Minimum trend score threshold
        dry_run: Whether to run in dry-run mode
        force: Force rescore even if already scored
        fetch_homepage: Whether to fetch homepage content
        concurrency: Concurrency level for domain work
        llm_concurrency: Concurrency level for LM Studio calls
        model: Optional LLM model name

    Returns:
        Number of domains processed
    """
    # Initialize repositories
    log_handler = _setup_logging()
    domain_repo = DomainRepository()
    observation_repo = ObservationRepository()
    stats = {
        "homepage_misses": 0,
    }
    domain_concurrency = max(1, concurrency)
    llm_concurrency = max(1, llm_concurrency)

    # Initialize LLM scorer
    settings = Settings()
    llm_semaphore = asyncio.Semaphore(llm_concurrency)
    scorer = OpportunityScorer(
        base_url=settings.lmstudio_base_url,
        model=model or settings.lmstudio_model,
        timeout=300.0,
        llm_semaphore=llm_semaphore,
    )

    # Build base query for domains (filters applied but without range)
    base_query = domain_repo._client.table("domains").select("*").order("latest_best_score", desc=True)

    # Apply filters
    if only_missing:
        base_query = base_query.is_("opportunity_score", None)

    if min_trend_score is not None:
        base_query = base_query.gte("trend_score", min_trend_score)

    # Paginate to bypass Supabase 1,000‑row limit
    batch_size = 1000
    offset = 0
    domains = []
    while True:
        try:
            batch = base_query.range(offset, offset + batch_size - 1).execute()
            rows = batch.data or []
        except Exception as e:
            logger.error(f"Failed to fetch domain batch (offset {offset}): {e}")
            await scorer.close()
            return 0
        if not rows:
            break
        domains.extend(rows)
        if len(rows) < batch_size:
            break
        offset += batch_size

    # Apply limit after pagination and filtering
    fetched_candidates = len(domains)
    skipped_failed = 0
    if only_missing and not force:
        before_status_filter = len(domains)
        domains = [row for row in domains if row.get("opportunity_score_status") != "failed"]
        skipped_failed = before_status_filter - len(domains)

    if limit:
        domains = domains[:limit]

    logger.info(
        "Processing %s domains "
        "(candidate_count=%s, domain_concurrency=%s, llm_concurrency=%s, model=%s, dry_run=%s, "
        "fetch_homepage=%s, skipped_failed=%s)",
        len(domains),
        fetched_candidates,
        domain_concurrency,
        llm_concurrency,
        scorer.model,
        dry_run,
        fetch_homepage,
        skipped_failed,
    )
    if only_missing and not force and not domains and skipped_failed:
        logger.warning(
            "No domains processed because %s missing-score domain(s) are marked failed. "
            "Run ./start-score --force to retry failed rows.",
            skipped_failed,
        )

    # Process domains with concurrency control
    semaphore = asyncio.Semaphore(domain_concurrency)

    async def process_with_semaphore(domain_row):
        async with semaphore:
            return await score_single_domain(
                domain_repo, observation_repo, scorer, domain_row, fetch_homepage, dry_run, stats
            )

    # Process domains in parallel
    successful = 0
    failed = 0

    tasks = [asyncio.create_task(process_with_semaphore(domain_row)) for domain_row in domains]
    for processed, task in enumerate(asyncio.as_completed(tasks), start=1):
        try:
            result = await task
        except Exception as exc:
            logger.error(f"Task failed: {exc}")
            failed += 1
            result = None

        if result is None:
            pass
        elif isinstance(result, Exception):
            logger.error(f"Task failed: {result}")
            failed += 1
        elif result.get("success"):
            logger.info(f"Scored {result['domain']}: {result['score']}")
            successful += 1
        else:
            logger.warning(f"Failed to score {result['domain']}: {result['error']}")
            failed += 1

        if processed % PROGRESS_LOG_INTERVAL == 0 or processed == len(domains):
            logger.info(
                "Progress: %s/%s processed (%s successful, %s failed)",
                processed,
                len(domains),
                successful,
                failed,
            )

    stats["validation_retries"] = scorer.validation_retries
    stats["lmstudio_429_retries"] = scorer.client.retry_counts.get("rate_limited", 0)
    stats["lmstudio_transient_retries"] = scorer.client.retry_counts.get("transient", 0)

    await scorer.close()

    logger.info(f"Processed {len(domains)} domains: {successful} successful, {failed} failed")
    logger.info(
        "Scoring stats: homepage_misses=%s, validation_retries=%s, lmstudio_429_retries=%s, "
        "lmstudio_transient_retries=%s",
        stats["homepage_misses"],
        stats["validation_retries"],
        stats["lmstudio_429_retries"],
        stats["lmstudio_transient_retries"],
    )
    logger.info(f"Log file: {log_handler.baseFilename}")
    return len(domains)


def cli(argv=None):
    """Command line interface for update-opportunity-scores."""
    parser = argparse.ArgumentParser(description="Update opportunity scores for domains using LLM")
    parser.add_argument(
        "--only-missing", action="store_true", help="Only score domains without existing opportunity scores"
    )
    parser.add_argument("--limit", type=int, help="Limit number of domains to process")
    parser.add_argument("--min-trend-score", type=float, help="Minimum trend score threshold")
    parser.add_argument("--dry-run", action="store_true", help="Print results without saving")
    parser.add_argument(
        "--force",
        action="store_true",
        help="Include previously failed missing-score rows; without --only-missing, rescore selected rows",
    )
    parser.add_argument("--fetch-homepage", action="store_true", help="Enable homepage fetching with BeautifulSoup")
    parser.add_argument(
        "--concurrency",
        type=int,
        default=5,
        help="Concurrency level for domain work such as DB/context/homepage (default: 5)",
    )
    parser.add_argument(
        "--llm-concurrency", type=int, default=1, help="Concurrency level for LM Studio calls (default: 1)"
    )

    parser.add_argument("--model", type=str, help="LLM model name to use")

    args = parser.parse_args(argv)

    try:
        asyncio.run(
            update_opportunity_scores(
                only_missing=args.only_missing,
                limit=args.limit,
                min_trend_score=args.min_trend_score,
                dry_run=args.dry_run,
                force=args.force,
                fetch_homepage=args.fetch_homepage,
                concurrency=args.concurrency,
                llm_concurrency=args.llm_concurrency,
                model=args.model,
            )
        )
        return 0
    except Exception as e:
        logger.error(f"Error in update-opportunity-scores: {e}")
        return 1


if __name__ == "__main__":
    # This allows direct execution
    import sys

    sys.exit(cli())
