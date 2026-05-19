from __future__ import annotations

from dataclasses import dataclass

import httpx

from src.config.settings import settings
from src.github_discovery.schemas import GitHubRepoSnapshot

GITHUB_SEARCH_REPOSITORIES_URL = "https://api.github.com/search/repositories"
GITHUB_TOPIC_SOURCE_URL = "https://github.com/topics/opencode?o=desc&s=stars"
DEFAULT_TOPIC = "opencode"
DEFAULT_TARGET_LIMIT = 500
GITHUB_PER_PAGE = 100


class GitHubAPIError(RuntimeError):
    """Raised when GitHub Search API returns an error or invalid payload."""


class GitHubRateLimitError(GitHubAPIError):
    """Raised when GitHub rate limits the search request."""


@dataclass(frozen=True)
class GitHubSearchPage:
    items: list[GitHubRepoSnapshot]
    incomplete_results: bool


class GitHubSearchClient:
    """Small GitHub Search API client for repository topic snapshots."""

    def __init__(
        self,
        token: str | None = None,
        timeout: float = 30.0,
        http_client: httpx.Client | None = None,
    ):
        self._token = token if token is not None else settings.github_token
        self._timeout = timeout
        self._http_client = http_client

    def fetch_topic_repositories(
        self,
        topic: str = DEFAULT_TOPIC,
        target_limit: int = DEFAULT_TARGET_LIMIT,
    ) -> list[GitHubRepoSnapshot]:
        repos: list[GitHubRepoSnapshot] = []
        max_pages = (target_limit + GITHUB_PER_PAGE - 1) // GITHUB_PER_PAGE
        max_pages = min(max_pages, 5)

        close_client = self._http_client is None
        client = self._http_client or httpx.Client(timeout=self._timeout)
        try:
            for page in range(1, max_pages + 1):
                page_result = self.fetch_topic_page(client, topic=topic, page=page)
                repos.extend(page_result.items)
                if len(page_result.items) < GITHUB_PER_PAGE or len(repos) >= target_limit:
                    break
            return repos[:target_limit]
        finally:
            if close_client:
                client.close()

    def fetch_topic_page(self, client: httpx.Client, topic: str, page: int) -> GitHubSearchPage:
        headers = {"Accept": "application/vnd.github+json"}
        if self._token:
            headers["Authorization"] = f"Bearer {self._token}"

        response = client.get(
            GITHUB_SEARCH_REPOSITORIES_URL,
            headers=headers,
            params={
                "q": f"topic:{topic}",
                "sort": "stars",
                "order": "desc",
                "per_page": GITHUB_PER_PAGE,
                "page": page,
            },
        )
        if response.status_code in (403, 429):
            remaining = response.headers.get("x-ratelimit-remaining")
            if remaining == "0" or response.status_code == 429:
                reset = response.headers.get("x-ratelimit-reset")
                suffix = f" Reset epoch: {reset}." if reset else ""
                raise GitHubRateLimitError(f"GitHub Search API rate limit exceeded.{suffix}")
        try:
            response.raise_for_status()
        except httpx.HTTPStatusError as exc:
            raise GitHubAPIError(f"GitHub Search API failed with HTTP {response.status_code}: {response.text}") from exc

        payload = response.json()
        items = payload.get("items")
        if not isinstance(items, list):
            raise GitHubAPIError("GitHub Search API response did not include an items list.")

        return GitHubSearchPage(
            items=[GitHubRepoSnapshot.from_api_item(item) for item in items],
            incomplete_results=bool(payload.get("incomplete_results", False)),
        )
