from __future__ import annotations

import httpx
import pytest
from app import data_loader

from src.github_discovery.client import GitHubAPIError, GitHubSearchClient
from src.github_discovery.crawler import GitHubOpencodeCrawler
from src.github_discovery.schemas import GitHubRepoSnapshot


def _repo(repo_id: int, stars: int = 100, forks: int = 10) -> GitHubRepoSnapshot:
    return GitHubRepoSnapshot(
        github_repo_id=repo_id,
        full_name=f"owner/repo-{repo_id}",
        owner="owner",
        repo_name=f"repo-{repo_id}",
        html_url=f"https://github.com/owner/repo-{repo_id}",
        description=f"Repo {repo_id}",
        language="Python",
        stargazers_count=stars,
        forks_count=forks,
        open_issues_count=repo_id,
        pushed_at="2026-05-18T10:00:00Z",
        updated_at="2026-05-18T11:00:00Z",
        created_at="2026-05-17T09:00:00Z",
    )


class FakeSearchClient:
    def __init__(self, repos: list[GitHubRepoSnapshot] | None = None, error: Exception | None = None):
        self.repos = repos or []
        self.error = error

    def fetch_topic_repositories(self, topic: str, target_limit: int) -> list[GitHubRepoSnapshot]:
        if self.error:
            raise self.error
        return self.repos[:target_limit]


class FakeGitHubRepository:
    def __init__(self, existing_ids: set[int] | None = None):
        self.existing_ids = existing_ids or set()
        self.inserted: list[dict] = []
        self.updated: list[GitHubRepoSnapshot] = []
        self.observations: list[dict] = []
        self.completed: dict | None = None
        self.failed_error: str | None = None

    def create_crawl_run(self, source_url: str, topic: str = "opencode", target_limit: int = 500) -> dict:
        return {"id": "run-1"}

    def get_existing_repo_ids(self) -> set[int]:
        return set(self.existing_ids)

    def insert_repository(
        self,
        repo: GitHubRepoSnapshot,
        run_id: str,
        is_baseline: bool,
        is_new: bool,
    ) -> dict:
        row = {
            "id": f"repo-{repo.github_repo_id}",
            "github_repo_id": repo.github_repo_id,
            "is_baseline": is_baseline,
            "is_new": is_new,
            "stargazers_count": repo.stargazers_count,
        }
        self.inserted.append(row)
        return row

    def insert_repositories(
        self,
        repos: list[GitHubRepoSnapshot],
        run_id: str,
        is_baseline: bool,
        is_new: bool,
    ) -> list[dict]:
        return [
            self.insert_repository(repo, run_id=run_id, is_baseline=is_baseline, is_new=is_new)
            for repo in repos
        ]

    def update_repository(self, repo: GitHubRepoSnapshot) -> dict:
        self.updated.append(repo)
        return {
            "id": f"repo-{repo.github_repo_id}",
            "github_repo_id": repo.github_repo_id,
            "stargazers_count": repo.stargazers_count,
        }

    def update_repositories(self, repos: list[GitHubRepoSnapshot]) -> list[dict]:
        return [self.update_repository(repo) for repo in repos]

    def get_repository_identity_map(self, github_repo_ids: list[int]) -> dict[int, str]:
        return {repo_id: f"repo-{repo_id}" for repo_id in github_repo_ids}

    def insert_observation(self, run_id: str, repository_id: str, rank: int, repo: GitHubRepoSnapshot) -> dict:
        row = {
            "run_id": run_id,
            "repository_id": repository_id,
            "rank": rank,
            "stars": repo.stargazers_count,
        }
        self.observations.append(row)
        return row

    def insert_observations(self, rows: list[dict]) -> list[dict]:
        self.observations.extend(rows)
        return rows

    def complete_crawl_run(
        self,
        run_id: str,
        fetched_count: int,
        new_count: int,
        baseline_count: int,
    ) -> dict:
        self.completed = {
            "run_id": run_id,
            "fetched_count": fetched_count,
            "new_count": new_count,
            "baseline_count": baseline_count,
        }
        return self.completed

    def fail_crawl_run(self, run_id: str, error: str) -> dict:
        self.failed_error = error
        return {"id": run_id, "status": "failed", "error": error}


def test_first_github_run_creates_baseline_and_no_new_repos():
    repo_store = FakeGitHubRepository()
    crawler = GitHubOpencodeCrawler(
        repository=repo_store,
        search_client=FakeSearchClient([_repo(1), _repo(2)]),
    )

    summary = crawler.run()

    assert summary.fetched_count == 2
    assert summary.new_count == 0
    assert summary.baseline_count == 2
    assert [row["is_baseline"] for row in repo_store.inserted] == [True, True]
    assert [row["is_new"] for row in repo_store.inserted] == [False, False]
    assert len(repo_store.observations) == 2


def test_second_github_run_with_same_repos_creates_no_new_repos():
    repo_store = FakeGitHubRepository(existing_ids={1, 2})
    crawler = GitHubOpencodeCrawler(
        repository=repo_store,
        search_client=FakeSearchClient([_repo(1), _repo(2)]),
    )

    summary = crawler.run()

    assert summary.new_count == 0
    assert summary.baseline_count == 0
    assert repo_store.inserted == []
    assert [repo.github_repo_id for repo in repo_store.updated] == [1, 2]


def test_second_github_run_marks_only_unseen_repo_as_new():
    repo_store = FakeGitHubRepository(existing_ids={1, 2})
    crawler = GitHubOpencodeCrawler(
        repository=repo_store,
        search_client=FakeSearchClient([_repo(1), _repo(3)]),
    )

    summary = crawler.run()

    assert summary.new_count == 1
    assert [row["github_repo_id"] for row in repo_store.inserted] == [3]
    assert repo_store.inserted[0]["is_baseline"] is False
    assert repo_store.inserted[0]["is_new"] is True
    assert [repo.github_repo_id for repo in repo_store.updated] == [1]


def test_existing_github_repos_get_updated_counts():
    repo_store = FakeGitHubRepository(existing_ids={1})
    crawler = GitHubOpencodeCrawler(
        repository=repo_store,
        search_client=FakeSearchClient([_repo(1, stars=999, forks=44)]),
    )

    crawler.run()

    assert repo_store.updated[0].stargazers_count == 999
    assert repo_store.updated[0].forks_count == 44
    assert repo_store.observations[0]["stars"] == 999


def test_failed_github_api_call_marks_run_failed():
    repo_store = FakeGitHubRepository()
    crawler = GitHubOpencodeCrawler(
        repository=repo_store,
        search_client=FakeSearchClient(error=GitHubAPIError("boom")),
    )

    with pytest.raises(GitHubAPIError):
        crawler.run()

    assert repo_store.failed_error == "boom"


def test_github_crawler_reports_progress():
    messages: list[str] = []
    repo_store = FakeGitHubRepository()
    crawler = GitHubOpencodeCrawler(
        repository=repo_store,
        search_client=FakeSearchClient([_repo(1)]),
        progress=messages.append,
    )

    crawler.run()

    assert messages[0].startswith("Creating GitHub crawl run")
    assert "Fetching repositories" in messages[1]
    assert any(message.startswith("Writing 1 crawl observations") for message in messages)


class FakeHTTPClient:
    def __init__(self, pages: list[list[dict]]):
        self.pages = pages
        self.calls: list[dict] = []

    def get(self, url: str, headers: dict, params: dict):
        self.calls.append({"url": url, "headers": headers, "params": params})
        page = int(params["page"])
        payload = {"items": self.pages[page - 1], "incomplete_results": False}
        return httpx.Response(200, json=payload, request=httpx.Request("GET", url))

    def close(self) -> None:
        pass


def _api_item(repo_id: int) -> dict:
    repo = _repo(repo_id)
    return {
        "id": repo.github_repo_id,
        "full_name": repo.full_name,
        "owner": {"login": repo.owner},
        "name": repo.repo_name,
        "html_url": repo.html_url,
        "description": repo.description,
        "language": repo.language,
        "stargazers_count": repo.stargazers_count,
        "forks_count": repo.forks_count,
        "open_issues_count": repo.open_issues_count,
        "pushed_at": repo.pushed_at,
        "updated_at": repo.updated_at,
        "created_at": repo.created_at,
    }


def test_github_client_stops_when_fewer_than_500_repos_are_available():
    http_client = FakeHTTPClient(pages=[[_api_item(1), _api_item(2)]])
    client = GitHubSearchClient(token=None, http_client=http_client)

    repos = client.fetch_topic_repositories(topic="opencode", target_limit=500)

    assert [repo.github_repo_id for repo in repos] == [1, 2]
    assert len(http_client.calls) == 1
    assert http_client.calls[0]["params"] == {
        "q": "topic:opencode",
        "sort": "stars",
        "order": "desc",
        "per_page": 100,
        "page": 1,
    }


def test_github_ui_query_excludes_baseline_repositories(monkeypatch):
    data_loader.load_new_github_repositories.clear()
    response = type("Response", (), {"data": []})()
    query = type("Query", (), {})()
    query.select = lambda *args, **kwargs: query
    query.eq = lambda *args, **kwargs: query
    query.order = lambda *args, **kwargs: query
    query.limit = lambda *args, **kwargs: query
    query.execute = lambda: response
    query.eq_calls = []

    def eq(column, value):
        query.eq_calls.append((column, value))
        return query

    query.eq = eq
    client = type("Client", (), {"table": lambda self, name: query})()
    monkeypatch.setattr(data_loader, "get_supabase_client", lambda: client)

    df = data_loader.load_new_github_repositories()

    assert df.empty
    assert ("is_baseline", False) in query.eq_calls
    assert ("is_new", True) in query.eq_calls
