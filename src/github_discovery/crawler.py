from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from src.db.repositories import GitHubRepositoryRepository
from src.github_discovery.client import DEFAULT_TARGET_LIMIT, DEFAULT_TOPIC, GITHUB_TOPIC_SOURCE_URL, GitHubSearchClient
from src.github_discovery.schemas import GitHubRepoSnapshot
from src.utils.logging import get_logger

logger = get_logger(__name__)


@dataclass(frozen=True)
class GitHubCrawlSummary:
    run_id: str
    status: str
    fetched_count: int
    new_count: int
    baseline_count: int


class GitHubOpencodeCrawler:
    """Crawl the GitHub opencode topic snapshot and persist repository deltas."""

    def __init__(
        self,
        repository: GitHubRepositoryRepository | None = None,
        search_client: GitHubSearchClient | None = None,
        topic: str = DEFAULT_TOPIC,
        target_limit: int = DEFAULT_TARGET_LIMIT,
        source_url: str = GITHUB_TOPIC_SOURCE_URL,
        progress: Callable[[str], None] | None = None,
    ):
        self._repository = repository or GitHubRepositoryRepository()
        self._search_client = search_client or GitHubSearchClient()
        self._topic = topic
        self._target_limit = target_limit
        self._source_url = source_url
        self._progress = progress

    def run(self) -> GitHubCrawlSummary:
        self._emit_progress(f"Creating GitHub crawl run for topic:{self._topic} (limit={self._target_limit})")
        run = self._repository.create_crawl_run(
            source_url=self._source_url,
            topic=self._topic,
            target_limit=self._target_limit,
        )
        run_id = str(run.get("id") or "")
        if not run_id:
            raise RuntimeError("Failed to create github_repo_crawl_runs row.")

        try:
            self._emit_progress("Fetching repositories from GitHub Search API...")
            repos = self._search_client.fetch_topic_repositories(topic=self._topic, target_limit=self._target_limit)
            self._emit_progress(f"Fetched {len(repos)} repositories. Loading existing repository ids...")
            existing_repo_ids = self._repository.get_existing_repo_ids()
            baseline_mode = len(existing_repo_ids) == 0
            saved_repositories: list[dict] = []

            if baseline_mode:
                self._emit_progress(f"Saving {len(repos)} baseline repositories...")
                saved_repositories = self._repository.insert_repositories(
                    repos,
                    run_id=run_id,
                    is_baseline=True,
                    is_new=False,
                )
                new_count = 0
                baseline_count = len(repos)
            else:
                existing_repos = [repo for repo in repos if repo.github_repo_id in existing_repo_ids]
                new_repos = [repo for repo in repos if repo.github_repo_id not in existing_repo_ids]
                if existing_repos:
                    self._emit_progress(f"Refreshing {len(existing_repos)} existing repositories...")
                    saved_repositories.extend(self._repository.update_repositories(existing_repos))
                if new_repos:
                    self._emit_progress(f"Saving {len(new_repos)} newly discovered repositories...")
                    saved_repositories.extend(
                        self._repository.insert_repositories(
                            new_repos,
                            run_id=run_id,
                            is_baseline=False,
                            is_new=True,
                        )
                    )
                    existing_repo_ids.update(repo.github_repo_id for repo in new_repos)
                new_count = len(new_repos)
                baseline_count = 0

            repository_ids = self._repository_ids_from_rows(saved_repositories)
            missing_identity_ids = [repo.github_repo_id for repo in repos if repo.github_repo_id not in repository_ids]
            if missing_identity_ids:
                repository_ids.update(self._repository.get_repository_identity_map(missing_identity_ids))

            observation_rows = self._build_observation_rows(run_id, repos, repository_ids)
            self._emit_progress(f"Writing {len(observation_rows)} crawl observations...")
            self._repository.insert_observations(observation_rows)

            self._repository.complete_crawl_run(
                run_id,
                fetched_count=len(repos),
                new_count=new_count,
                baseline_count=baseline_count,
            )
            logger.info(
                "Completed GitHub opencode crawl: fetched={}, new={}, baseline={}",
                len(repos),
                new_count,
                baseline_count,
            )
            return GitHubCrawlSummary(
                run_id=run_id,
                status="completed",
                fetched_count=len(repos),
                new_count=new_count,
                baseline_count=baseline_count,
            )
        except Exception as exc:
            self._repository.fail_crawl_run(run_id, str(exc))
            logger.exception("GitHub opencode crawl failed")
            raise

    def _emit_progress(self, message: str) -> None:
        if self._progress:
            self._progress(message)

    def _repository_ids_from_rows(self, rows: list[dict]) -> dict[int, str]:
        return {
            int(row["github_repo_id"]): str(row["id"])
            for row in rows
            if row.get("github_repo_id") is not None and row.get("id")
        }

    def _build_observation_rows(
        self,
        run_id: str,
        repos: list[GitHubRepoSnapshot],
        repository_ids: dict[int, str],
    ) -> list[dict]:
        rows: list[dict] = []
        for rank, repo in enumerate(repos, start=1):
            repository_id = repository_ids.get(repo.github_repo_id)
            if not repository_id:
                logger.warning(
                    "Skipping GitHub observation for {} because no repository id was returned.",
                    repo.full_name,
                )
                continue
            rows.append(
                {
                    "run_id": run_id,
                    "repository_id": repository_id,
                    "rank": rank,
                    "stars": repo.stargazers_count,
                    "forks": repo.forks_count,
                    "open_issues": repo.open_issues_count,
                }
            )
        return rows
