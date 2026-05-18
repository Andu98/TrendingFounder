"""LLM scorer for opportunity scoring."""

import asyncio
import logging
from typing import Any

from pydantic import ValidationError

from src.llm.lmstudio_client import LMStudioClient
from src.opportunity.schemas import OpportunityScoreResult

logger = logging.getLogger(__name__)


class OpportunityScorer:
    """Scorer that uses an LLM to evaluate domain opportunities."""

    def __init__(
        self,
        base_url: str | None = None,
        model: str | None = None,
        timeout: float = 300.0,
        llm_semaphore: asyncio.Semaphore | None = None,
    ):
        """
        Initialize the opportunity scorer.

        Args:
            base_url: Base URL for the LLM API
            model: Model name to use
            timeout: Request timeout in seconds
            llm_semaphore: Optional shared semaphore limiting concurrent LLM calls
        """
        self.client = LMStudioClient(base_url=base_url, model=model, timeout=timeout)
        self.model = model or "qwen-local"
        self._llm_semaphore = llm_semaphore
        self.validation_retries = 0

    async def close(self) -> None:
        await self.client.close()

    async def _call_llm(self, prompt: str) -> dict:
        if self._llm_semaphore is None:
            return await self.client.call_json_schema(
                prompt=prompt,
                schema_name="OpportunityScoreResult",
                schema=OpportunityScoreResult.llm_json_schema(),
                temperature=0.1,
                max_tokens=1400,
            )

        async with self._llm_semaphore:
            return await self.client.call_json_schema(
                prompt=prompt,
                schema_name="OpportunityScoreResult",
                schema=OpportunityScoreResult.llm_json_schema(),
                temperature=0.1,
                max_tokens=1400,
            )

    async def score_domain(
        self,
        context: dict[str, Any],
        homepage_excerpt: str | None = None,
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
            homepage_excerpt=homepage_excerpt,
        )

        response = await self._call_llm(prompt)

        try:
            return OpportunityScoreResult.model_validate(response)
        except ValidationError as exc:
            self.validation_retries += 1
            logger.warning(f"Opportunity scoring validation failed; retrying once with stricter prompt: {exc}")

        repair_prompt = (
            f"{prompt}\n\n"
            "IMPORTANT: Return only valid JSON matching the schema. "
            "Every required string field must contain a string, never null. "
            "If you have no useful idea, use a concise sentence explaining that."
        )
        response = await self._call_llm(repair_prompt)
        return OpportunityScoreResult.model_validate(response)
