from unittest.mock import MagicMock

import pytest

from src.config.constants import GitHubRepoReviewStatus, ReviewStatus
from src.db.repositories import (
    CommentRepository,
    CrawlCountryStatusRepository,
    CrawlRunRepository,
    DomainRepository,
    GitHubRepositoryRepository,
    ObservationRepository,
)


@pytest.fixture
def mock_client():
    return MagicMock()


@pytest.fixture
def mock_response():
    response = MagicMock()
    response.data = [{"id": "test-uuid-1", "normalized_domain": "example.com"}]
    return response


class TestDomainRepository:
    def test_upsert_domain(self, mock_client, mock_response):
        mock_client.table.return_value.upsert.return_value.execute.return_value = mock_response

        repo = DomainRepository(client=mock_client)
        result = repo.upsert_domain("example.com", display_url="https://example.com")

        mock_client.table.assert_called_with("domains")
        assert result["id"] == "test-uuid-1"

    def test_get_by_normalized_domain_found(self, mock_client):
        response = MagicMock()
        response.data = [{"id": "test-uuid-1", "normalized_domain": "example.com"}]
        mock_client.table.return_value.select.return_value.eq.return_value.execute.return_value = response

        repo = DomainRepository(client=mock_client)
        result = repo.get_by_normalized_domain("example.com")

        assert result is not None
        assert result["normalized_domain"] == "example.com"

    def test_get_by_normalized_domain_not_found(self, mock_client):
        response = MagicMock()
        response.data = []
        mock_client.table.return_value.select.return_value.eq.return_value.execute.return_value = response

        repo = DomainRepository(client=mock_client)
        result = repo.get_by_normalized_domain("nonexistent.com")

        assert result is None

    def test_update_review_status(self, mock_client, mock_response):
        mock_client.table.return_value.update.return_value.eq.return_value.execute.return_value = mock_response

        repo = DomainRepository(client=mock_client)
        result = repo.update_review_status("test-uuid-1", ReviewStatus.OK)

        assert result["id"] == "test-uuid-1"


class TestObservationRepository:
    def test_insert_observation(self, mock_client):
        response = MagicMock()
        response.data = [{"id": "obs-uuid-1"}]
        mock_client.table.return_value.upsert.return_value.execute.return_value = response

        from datetime import date

        repo = ObservationRepository(client=mock_client)
        result = repo.insert_observation(
            domain_id="test-domain-id",
            crawl_run_id="test-run-id",
            observed_date=date.today(),
            country_code="US",
            country_name="United States",
            ranking_type="trending_rise",
            rank=1,
            pct_rank_change=150.0,
        )

        mock_client.table.assert_called_with("domain_observations")
        assert result["id"] == "obs-uuid-1"


class TestCrawlRunRepository:
    def test_create_run(self, mock_client):
        response = MagicMock()
        response.data = [{"id": "run-uuid-1", "status": "running"}]
        mock_client.table.return_value.insert.return_value.execute.return_value = response

        repo = CrawlRunRepository(client=mock_client)
        result = repo.create_run()

        mock_client.table.assert_called_with("crawl_runs")
        assert result["id"] == "run-uuid-1"

    def test_complete_run(self, mock_client):
        response = MagicMock()
        response.data = [{"id": "run-uuid-1", "status": "completed"}]
        mock_client.table.return_value.update.return_value.eq.return_value.execute.return_value = response

        repo = CrawlRunRepository(client=mock_client)
        result = repo.complete_run("run-uuid-1")

        assert result["status"] == "completed"

    def test_get_today_run_found(self, mock_client):
        response = MagicMock()
        response.data = [{"id": "run-uuid-1", "status": "running"}]
        mock_client.table.return_value.select.return_value.eq.return_value.execute.return_value = response

        repo = CrawlRunRepository(client=mock_client)
        result = repo.get_today_run()

        assert result is not None
        assert result["id"] == "run-uuid-1"

    def test_get_today_run_not_found(self, mock_client):
        response = MagicMock()
        response.data = []
        mock_client.table.return_value.select.return_value.eq.return_value.execute.return_value = response

        repo = CrawlRunRepository(client=mock_client)
        result = repo.get_today_run()

        assert result is None


class TestCrawlCountryStatusRepository:
    def test_upsert_country_status(self, mock_client):
        response = MagicMock()
        response.data = [{"id": "status-uuid-1"}]
        mock_client.table.return_value.upsert.return_value.execute.return_value = response

        repo = CrawlCountryStatusRepository(client=mock_client)
        result = repo.upsert_country_status(
            crawl_run_id="run-uuid-1",
            country_code="US",
            country_name="United States",
            status="completed",
            items_found=50,
        )

        mock_client.table.assert_called_with("crawl_country_status")
        assert result["id"] == "status-uuid-1"


class TestGitHubRepositoryRepository:
    def test_mark_seen_many_updates_visible_repository_ids(self, mock_client):
        response = MagicMock()
        response.data = [{"id": "repo-1"}, {"id": "repo-2"}]
        mock_client.table.return_value.update.return_value.in_.return_value.execute.return_value = response

        repo = GitHubRepositoryRepository(client=mock_client)
        result = repo.mark_seen_many(["repo-1", "repo-2"])

        mock_client.table.assert_called_with("github_repositories")
        mock_client.table.return_value.update.assert_called_once_with(
            {
                "is_new": False,
                "review_status": GitHubRepoReviewStatus.IGNORED.value,
            }
        )
        mock_client.table.return_value.update.return_value.in_.assert_called_once_with("id", ["repo-1", "repo-2"])
        assert result == 2


class TestCommentRepository:
    def test_add_comment(self, mock_client):
        response = MagicMock()
        response.data = [{"id": "comment-uuid-1"}]
        mock_client.table.return_value.insert.return_value.execute.return_value = response

        repo = CommentRepository(client=mock_client)
        result = repo.add_comment("domain-uuid-1", "Alice", "Looks interesting")

        assert result["id"] == "comment-uuid-1"

    def test_get_comments(self, mock_client):
        response = MagicMock()
        response.data = [
            {"id": "c1", "message": "First"},
            {"id": "c2", "message": "Second"},
        ]
        chain = mock_client.table.return_value.select.return_value.eq.return_value.order.return_value
        chain.execute.return_value = response

        repo = CommentRepository(client=mock_client)
        result = repo.get_comments("domain-uuid-1")

        assert len(result) == 2
        assert result[0]["message"] == "First"

    def test_get_comments_empty(self, mock_client):
        response = MagicMock()
        response.data = []
        chain = mock_client.table.return_value.select.return_value.eq.return_value.order.return_value
        chain.execute.return_value = response

        repo = CommentRepository(client=mock_client)
        result = repo.get_comments("domain-uuid-1")

        assert result == []
