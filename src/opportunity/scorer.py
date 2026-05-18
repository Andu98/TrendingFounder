"""LLM scorer for opportunity scoring."""

import asyncio
import json
import logging
from typing import Optional, Dict, Any
from pydantic import ValidationError

import httpx
from src.opportunity.schemas import OpportunityScoreResult
from src.llm.lmstudio_client import LMStudioClient


logger = logging.getLogger(__name__)


class OpportunityScorer:
    """Scorer that uses an LLM to evaluate domain opportunities."""
    
    def __init__(
        self,
        base_url: Optional[str] = None,
        model: Optional[str] = None,
        timeout: float = 300.0
    ):
        """
        Initialize the opportunity scorer.
        
        Args:
            base_url: Base URL for the LLM API
            model: Model name to use
            timeout: Request timeout in seconds
        """
        self.client = LMStudioClient(base_url=base_url, model=model, timeout=timeout)
        self.model = model or "qwen-local"
    
    async def score_domain(
        self,
        context: Dict[str, Any],
        homepage_excerpt: Optional[str] = None
    ) -> OpportunityScoreResult:
        """
        Score a domain using the LLM.
        
        Args:
            context: Dictionary with domain context information
            homepage_excerpt: Optional homepage excerpt
            
        Returns:
            OpportunityScoreResult with the LLM's evaluation
            
        Raises:
            Exception: If scoring fails after retries
        """
        # Build the prompt
        from src.opportunity.prompt import build_opportunity_prompt
        prompt = build_opportunity_prompt(
            domain=context.get("domain", ""),
            display_url=context.get("display_url", ""),
            trend_score=context.get("trend_score", 0.0),
            countries_observed=context.get("countries_observed", []),
            ranking_types=context.get("ranking_types", []),
            best_rank=context.get("best_rank", 0),
            pct_rank_change=context.get("pct_rank_change"),
            first_seen_at=context.get("first_seen_at", ""),
            existing_category=context.get("existing_category"),
            existing_summary=context.get("existing_summary"),
            existing_llm_potential=context.get("existing_llm_potential"),
            review_status=context.get("review_status", "pending"),
            romanian_signals=context.get("romanian_signals", False),
            homepage_excerpt=homepage_excerpt
        )
        
        # Call the LLM with retries
        max_retries = 3
        for attempt in range(max_retries + 1):
            try:
                # Get response from LLM
                response = await self.client.call(prompt, temperature=0.1)
                
                # Try to parse the JSON
                try:
                    # Try to validate it against our schema
                    result = OpportunityScoreResult(**response)
                    return result
                except ValidationError as e:
                    logger.warning(f"Validation error on attempt {attempt + 1}: {e}")
                    if attempt == max_retries:
                        raise Exception(f"Failed to validate LLM response after {max_retries + 1} attempts: {response}")
                    
                    # Retry with a slightly different prompt that emphasizes strict JSON
                    prompt += "\n\nIMPORTANT: Return ONLY VALID JSON with the exact schema provided. Do not include any explanations or additional text."
                    continue
                    
            except Exception as e:
                logger.warning(f"LLM call failed on attempt {attempt + 1}: {e}")
                if attempt == max_retries:
                    raise
                # Wait before retrying
                await asyncio.sleep(2 ** attempt)  # Exponential backoff
                
        # Should not reach here
        raise Exception("Unexpected error in scoring")