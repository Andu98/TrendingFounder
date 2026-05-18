"""Main command for updating opportunity scores using LLM."""

import argparse
import asyncio
import logging
from datetime import datetime
from typing import Optional, Dict, Any
import json

import httpx
from bs4 import BeautifulSoup

from src.db.repositories import DomainRepository, ObservationRepository
from src.opportunity.scorer import OpportunityScorer
from src.opportunity.constants import KNOWN_GLOBAL_GIANTS
from src.opportunity.schemas import OpportunityScoreResult
from src.llm.lmstudio_client import LMStudioClient
from src.config.settings import Settings
from src.db.supabase_client import get_supabase_client

logger = logging.getLogger(__name__)


def is_known_global_giant(domain: str) -> bool:
    """Check if a domain is in the known global giants set."""
    return domain.lower() in KNOWN_GLOBAL_GIANTS


def apply_giant_cap(domain: str, score: int) -> int:
    """Apply the global giant cap if needed."""
    if is_known_global_giant(domain) and score > 20:
        return 20
    return score


async def fetch_homepage_excerpt(url: str) -> Optional[str]:
    """
    Fetch and extract key information from a domain's homepage.
    
    Args:
        url: The URL to fetch
        
    Returns:
        Extracted content or None if failed
    """
    try:
        async with httpx.AsyncClient(timeout=5.0, follow_redirects=True) as client:
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
    existing_llm_summary: Optional[str],
    existing_llm_category: Optional[str],
    existing_llm_potential: Optional[int],
    first_seen_at: str
) -> Dict[str, Any]:
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
            observation_repo._client.table("domain_observations")
            .select("*")
            .eq("domain_id", domain_id)
            .execute()
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
    best_rank = min(obs.get("rank", float('inf')) for obs in observations) if observations else 0
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
    dry_run: bool
) -> Dict[str, Any]:
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
        domain_repo, observation_repo, domain_id, domain, display_url,
        review_status, existing_llm_summary, existing_llm_category, existing_llm_potential, first_seen_at
    )
    
    # Optionally fetch homepage
    homepage_excerpt = None
    if fetch_homepage and not dry_run:
        try:
            homepage_excerpt = await fetch_homepage_excerpt(display_url)
            if homepage_excerpt is None:
                logger.warning(f"Skipping LLM scoring for {domain}: Homepage crawl returned no content.")
                # Update DB to record the crawl failure
                update = {
                    "opportunity_breakdown": {
                        "error": "CrawlFailure",
                        "message": "Homepage crawl failed or returned no content. Scoring skipped to avoid hallucination."
                    },
                    "llm_opportunity_updated_at": datetime.utcnow().isoformat(),
                }
                if not dry_run:
                    domain_repo.update_opportunity_fields(domain_id, update)
                
                return {
                    "success": False,
                    "domain": domain,
                    "score": None,
                    "update": update,
                    "error": "Homepage crawl failed or returned no content"
                }
        except Exception as e:
            logger.warning(f"Failed to fetch homepage for {domain}: {e}")
            return {
                "success": False,
                "domain": domain,
                "score": None,
                "error": f"Homepage crawl error: {e}"
            }
    
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
            "llm_opportunity_updated_at": datetime.utcnow().isoformat(),
        }
        
        if not dry_run:
            domain_repo.update_opportunity_fields(domain_id, update)
        
        return {
            "success": True,
            "domain": domain,
            "score": final_score,
            "update": update,
            "error": None
        }
        
    except Exception as e:
        logger.error(f"Failed to score domain {domain}: {e}")
        
        # For failed scoring, preserve existing score if present, or set to 0
        update = {
            "opportunity_breakdown": {
                "error": str(type(e).__name__),
                "message": str(e)
            },
            "llm_opportunity_model": scorer.model,
            "llm_opportunity_prompt_version": "romania_llm_score_v1",
            "llm_opportunity_updated_at": datetime.utcnow().isoformat(),
        }
        
        if not dry_run:
            domain_repo.update_opportunity_fields(domain_id, update)
        
        return {
            "success": False,
            "domain": domain,
            "score": None,
            "update": update,
            "error": str(e)
        }


async def update_opportunity_scores(
    only_missing: bool = False,
    limit: Optional[int] = None,
    min_trend_score: Optional[float] = None,
    dry_run: bool = False,
    force: bool = False,
    fetch_homepage: bool = False,
    concurrency: int = 5
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
        concurrency: Concurrency level for LLM calls
        
    Returns:
        Number of domains processed
    """
    # Initialize repositories
    domain_repo = DomainRepository()
    observation_repo = ObservationRepository()
    
    # Initialize LLM scorer
    settings = Settings()
    scorer = OpportunityScorer(
        base_url=settings.lmstudio_base_url,
        model=settings.lmstudio_model,
        timeout=300.0
    )
    
    # Build query for domains
    query = domain_repo._client.table("domains").select("*").order("latest_best_score", desc=True)
    
    # Apply filters
    if only_missing and not force:
        query = query.is_("opportunity_score", None)
    
    if min_trend_score is not None:
        query = query.gte("trend_score", min_trend_score)
    
    # Execute query
    try:
        result = query.execute()
        domains = result.data or []
    except Exception as e:
        logger.error(f"Failed to fetch domains: {e}")
        return 0
    
    # Apply limit after filtering
    if limit:
        domains = domains[:limit]
    
    logger.info(f"Processing {len(domains)} domains")
    
    # Process domains with concurrency control
    semaphore = asyncio.Semaphore(concurrency)
    
    async def process_with_semaphore(domain_row):
        async with semaphore:
            return await score_single_domain(
                domain_repo, observation_repo, scorer, domain_row, fetch_homepage, dry_run
            )
    
    # Process domains in parallel
    tasks = [process_with_semaphore(domain_row) for domain_row in domains]
    results = await asyncio.gather(*tasks, return_exceptions=True)
    
    # Count successful and failed
    successful = 0
    failed = 0
    
    for result in results:
        if isinstance(result, Exception):
            logger.error(f"Task failed: {result}")
            failed += 1
        elif result.get("success"):
            logger.info(f"Scored {result['domain']}: {result['score']}")
            successful += 1
        else:
            logger.warning(f"Failed to score {result['domain']}: {result['error']}")
            failed += 1
    
    logger.info(f"Processed {len(domains)} domains: {successful} successful, {failed} failed")
    return len(domains)


def cli(argv=None):
    """Command line interface for update-opportunity-scores."""
    parser = argparse.ArgumentParser(
        description="Update opportunity scores for domains using LLM"
    )
    parser.add_argument(
        "--only-missing",
        action="store_true",
        help="Only score domains without existing opportunity scores"
    )
    parser.add_argument(
        "--limit",
        type=int,
        help="Limit number of domains to process"
    )
    parser.add_argument(
        "--min-trend-score",
        type=float,
        help="Minimum trend score threshold"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print results without saving"
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Rescore even if already scored"
    )
    parser.add_argument(
        "--fetch-homepage",
        action="store_true",
        help="Enable homepage fetching with BeautifulSoup"
    )
    parser.add_argument(
        "--concurrency",
        type=int,
        default=5,
        help="Concurrency level for LLM calls (default: 5)"
    )
    
    args = parser.parse_args(argv)
    
    try:
        count = asyncio.run(update_opportunity_scores(
            only_missing=args.only_missing,
            limit=args.limit,
            min_trend_score=args.min_trend_score,
            dry_run=args.dry_run,
            force=args.force,
            fetch_homepage=args.fetch_homepage,
            concurrency=args.concurrency
        ))
        return 0
    except Exception as e:
        logger.error(f"Error in update-opportunity-scores: {e}")
        return 1


if __name__ == "__main__":
    # This allows direct execution
    import sys
    sys.exit(cli())