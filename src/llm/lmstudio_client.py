import json
from typing import Any

import httpx
from loguru import logger as loguru_logger
from pydantic import ValidationError
from tenacity import (
    before_sleep_log,
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from src.config.settings import settings
from src.domains.normalize import is_known_giant
from src.llm.prompts import SYSTEM_PROMPT, build_enrichment_prompt
from src.llm.schemas import LLMEnrichmentResult
from src.utils.logging import get_logger

logger = get_logger(__name__)


class LMStudioClient:
    def __init__(
        self,
        base_url: str | None = None,
        model: str | None = None,
        timeout: float = 60.0,
    ):
        self._base_url = (base_url or settings.lmstudio_base_url).rstrip("/")
        self._model = model or settings.lmstudio_model
        self._timeout = timeout
        self._client: httpx.AsyncClient | None = None

    def _get_client(self) -> httpx.AsyncClient:
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(
                timeout=self._timeout,
                headers={"Content-Type": "application/json"},
            )
        return self._client

    async def close(self) -> None:
        if self._client and not self._client.is_closed:
            await self._client.aclose()
            self._client = None

    async def __aenter__(self):
        return self

    async def __aexit__(self, *exc):
        await self.close()

    def _build_payload(self, prompt: str) -> dict:
        return {
            "model": self._model,
            "messages": [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": prompt},
            ],
            "temperature": 0.1,
            "max_tokens": 512,
            "response_format": {
                "type": "json_schema",
                "json_schema": {
                    "name": "LLMEnrichmentResult",
                    "schema": {
                        "type": "object",
                        "properties": {
                            "summary": {"type": "string"},
                            "category": {"type": "string"},
                            "business_model": {"type": "string"},
                            "target_users": {"type": "string"},
                            "localization_angle": {"type": "string"},
                            "risk_notes": {"type": "string"},
                            "novelty": {"type": "integer", "minimum": 1, "maximum": 5},
                            "idea_potential": {"type": "integer", "minimum": 1, "maximum": 5},
                            "confidence": {"type": "integer", "minimum": 1, "maximum": 5},
                        },
                        "required": [
                            "summary",
                            "category",
                            "business_model",
                            "target_users",
                            "localization_angle",
                            "risk_notes",
                            "novelty",
                            "idea_potential",
                            "confidence",
                        ],
                        "additionalProperties": False,
                    },
                },
            },
        }

    @retry(
        retry=retry_if_exception_type((httpx.HTTPStatusError, httpx.ConnectError, httpx.TimeoutException)),
        stop=stop_after_attempt(4),
        wait=wait_exponential(multiplier=1, min=2, max=30),
        before_sleep=before_sleep_log(loguru_logger, "WARNING"),
        reraise=True,
    )
    async def _post(self, payload: dict) -> httpx.Response:
        client = self._get_client()
        response = await client.post(
            f"{self._base_url}/chat/completions",
            json=payload,
        )
        response.raise_for_status()
        return response

    async def enrich(
        self,
        domain: str,
        title: str | None = None,
        meta_description: str | None = None,
        categories: list[dict] | None = None,
        country_code: str | None = None,
        ranking_type: str | None = None,
        rank: int | None = None,
        pct_rank_change: float | None = None,
        homepage_snippet: str | None = None,
    ) -> LLMEnrichmentResult:
        if is_known_giant(domain):
            return LLMEnrichmentResult.failed(
                domain=domain,
                error="Skipped: known giant domain.",
            )

        prompt = build_enrichment_prompt(
            domain=domain,
            title=title,
            meta_description=meta_description,
            categories=categories,
            country_code=country_code,
            ranking_type=ranking_type,
            rank=rank,
            pct_rank_change=pct_rank_change,
            homepage_snippet=homepage_snippet,
        )

        payload = self._build_payload(prompt)

        try:
            response = await self._post(payload)
        except httpx.HTTPError as exc:
            logger.error(f"LM Studio request failed for {domain}: {exc}")
            return LLMEnrichmentResult.failed(
                domain=domain,
                error=f"HTTP error: {exc}",
            )

        try:
            data = response.json()
            content = data["choices"][0]["message"]["content"]
        except (KeyError, IndexError, TypeError) as exc:
            logger.error(f"Unexpected LM Studio response shape for {domain}: {exc}")
            return LLMEnrichmentResult.failed(
                domain=domain,
                error=f"Unexpected response shape: {exc}",
            )

        return self._parse_response(content, domain)

    def _parse_response(self, content: str, domain: str) -> LLMEnrichmentResult:
        content = content.strip()

        if content.startswith("```"):
            content = content.split("\n", 1)[-1].rsplit("```", 1)[0].strip()

        try:
            parsed: dict[str, Any] = json.loads(content)
        except json.JSONDecodeError as exc:
            logger.error(f"Invalid JSON from LLM for {domain}: {exc}")
            return LLMEnrichmentResult.failed(
                domain=domain,
                error=f"Invalid JSON: {exc}",
            )

        try:
            result = LLMEnrichmentResult.model_validate(parsed)
        except ValidationError as exc:
            logger.error(f"LLM response validation failed for {domain}: {exc}")
            return LLMEnrichmentResult.failed(
                domain=domain,
                error=f"Validation error: {exc}",
            )

        if is_known_giant(domain):
            result.risk_notes = f"{result.risk_notes or ''} Known giant domain.".strip()

        logger.info(f"LLM enrichment successful for {domain}")
        return result
