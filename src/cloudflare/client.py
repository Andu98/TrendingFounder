"""Async client for Cloudflare API with retry and rate‑limit handling.

Provides the CloudflareClient class for making authenticated async HTTP requests to the Cloudflare Radar service, with automatic retries, exponential back‑off, and rate‑limit handling.
"""

import httpx
from loguru import logger as loguru_logger
from tenacity import (
    before_sleep_log,
    retry,
    retry_if_exception,
    stop_after_attempt,
    wait_exponential,
)

from src.config.settings import settings
from src.utils.logging import get_logger

logger = get_logger(__name__)

RATE_LIMIT_RETRY_AFTER_HEADER = "retry-after"


class CloudflareAPIError(Exception):
    def __init__(self, status_code: int, message: str, response_body: str | None = None):
        self.status_code = status_code
        self.response_body = response_body
        super().__init__(message)


def _is_retryable(exc: BaseException) -> bool:
    if isinstance(exc, (httpx.ConnectError, httpx.TimeoutException)):
        return True
    if isinstance(exc, httpx.HTTPStatusError):
        return True
    if isinstance(exc, CloudflareAPIError):
        return exc.status_code >= 500
    return False



class CloudflareClient:
    """Async HTTP client for Cloudflare Radar API.

    Handles authentication, request retries, exponential back‑off, and rate‑limit handling.
    Provides ``request`` and ``get`` convenience methods.
    """
    BASE_URL = "https://api.cloudflare.com/client/v4"

    def __init__(self, api_token: str | None = None, timeout: float = 30.0):
        self._token = api_token or settings.cloudflare_api_token
        self._timeout = timeout
        self._client: httpx.AsyncClient | None = None

    def _get_client(self) -> httpx.AsyncClient:
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(
                base_url=self.BASE_URL,
                timeout=self._timeout,
                headers={
                    "Authorization": f"Bearer {self._token}",
                    "Content-Type": "application/json",
                },
            )
        return self._client

    async def _check_rate_limit(self, response: httpx.Response) -> None:
        if response.status_code == 429:
            retry_after = response.headers.get(RATE_LIMIT_RETRY_AFTER_HEADER)
            wait_seconds = float(retry_after) if retry_after else 5.0
            logger.warning(f"Rate limited by Cloudflare. Waiting {wait_seconds}s before retry.")
            raise httpx.HTTPStatusError(
                f"Rate limited (429). Retry after {wait_seconds}s.",
                request=response.request,
                response=response,
            )

    @retry(
        retry=retry_if_exception(_is_retryable),
        stop=stop_after_attempt(5),
        wait=wait_exponential(multiplier=2, min=4, max=60),
        before_sleep=before_sleep_log(loguru_logger, "WARNING"),
        reraise=True,
    )
    async def request(
        self,
        method: str,
        path: str,
        params: dict | None = None,
    ) -> httpx.Response:
        client = self._get_client()
        response = await client.request(method, path, params=params)

        await self._check_rate_limit(response)

        if response.status_code >= 400:
            body = response.text
            logger.error(f"Cloudflare API error {response.status_code} on {method} {path}: {body[:500]}")
            raise CloudflareAPIError(
                status_code=response.status_code,
                message=f"API error {response.status_code}: {response.reason_phrase}",
                response_body=body,
            )

        return response

    async def get(self, path: str, params: dict | None = None) -> httpx.Response:
        return await self.request("GET", path, params=params)

    async def close(self) -> None:
        if self._client and not self._client.is_closed:
            await self._client.aclose()
            self._client = None

    async def __aenter__(self):
        return self

    async def __aexit__(self, *exc):
        await self.close()
