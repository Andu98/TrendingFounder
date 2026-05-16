from dataclasses import dataclass
from datetime import date, datetime

from src.db.repositories import DomainRepository, ObservationRepository
from src.domains.normalize import build_display_url, normalize_domain
from src.utils.logging import get_logger

logger = get_logger(__name__)


@dataclass
class DedupeResult:
    domain_id: str
    is_new: bool
    normalized_domain: str


def dedupe_and_insert(
    domain_repo: DomainRepository,
    observation_repo: ObservationRepository,
    raw_domain: str,
    crawl_run_id: str | None,
    observed_date: date,
    country_code: str,
    country_name: str,
    ranking_type: str,
    rank: int,
    pct_rank_change: float | None = None,
    categories: list | None = None,
    observation_score: float | None = None,
    raw_payload: dict | None = None,
) -> DedupeResult:
    """Deduplicate a raw domain string and insert observation.

    Returns:
        DedupeResult with domain_id and is_new flag.
        If is_new is True, the caller should run LLM enrichment.
    """
    normalized = normalize_domain(raw_domain)

    existing = domain_repo.get_by_normalized_domain(normalized)

    if existing:
        logger.debug(f"Domain {normalized} already exists (id={existing['id']}). Skipping LLM.")
        domain_id = existing["id"]
        is_new = False
    else:
        display_url = build_display_url(normalized)
        result = domain_repo.upsert_domain(
            normalized_domain=normalized,
            display_url=display_url,
            first_seen_at=datetime.now(),
            first_seen_date=observed_date,
            first_country_code=country_code,
            first_country_name=country_name,
            first_ranking_type=ranking_type,
        )
        domain_id = result["id"]
        is_new = True
        logger.info(f"New domain discovered: {normalized}")

    observation_repo.insert_observation(
        domain_id=domain_id,
        crawl_run_id=crawl_run_id,
        observed_date=observed_date,
        country_code=country_code,
        country_name=country_name,
        ranking_type=ranking_type,
        rank=rank,
        pct_rank_change=pct_rank_change,
        categories=categories,
        observation_score=observation_score,
        raw_payload=raw_payload,
    )

    return DedupeResult(
        domain_id=domain_id,
        is_new=is_new,
        normalized_domain=normalized,
    )
