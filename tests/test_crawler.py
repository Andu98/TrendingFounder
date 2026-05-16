from datetime import date
from unittest.mock import AsyncMock, MagicMock

import pytest

from src.crawler.orchestrator import CrawlOrchestrator
from src.crawler.progress import format_progress, get_or_create_today_run


class TestFormatProgress:
    def test_zero_total(self):
        result = format_progress({"status": "running", "countries_total": 0})
        assert "no countries queued" in result

    def test_partial_progress(self):
        result = format_progress(
            {
                "status": "running",
                "countries_total": 200,
                "countries_completed": 50,
                "countries_failed": 2,
            }
        )
        assert "50/200" in result
        assert "25%" in result
        assert "2 failed" in result

    def test_completed(self):
        result = format_progress(
            {
                "status": "completed",
                "countries_total": 200,
                "countries_completed": 200,
                "countries_failed": 0,
            }
        )
        assert "100%" in result
        assert "completed" in result


class TestGetOrCreateTodayRun:
    def test_creates_new_run_when_none_exists(self):
        crawl_run_repo = MagicMock()
        crawl_run_repo.get_today_run.return_value = None
        crawl_run_repo.create_run.return_value = {"id": "new-run"}

        country_status_repo = MagicMock()

        result = get_or_create_today_run(crawl_run_repo, country_status_repo)

        crawl_run_repo.create_run.assert_called_once()
        assert result["resume"] is False

    def test_resumes_existing_running_run(self):
        existing = {"id": "existing-run", "status": "running"}
        crawl_run_repo = MagicMock()
        crawl_run_repo.get_today_run.return_value = existing

        country_status_repo = MagicMock()

        result = get_or_create_today_run(crawl_run_repo, country_status_repo)

        crawl_run_repo.create_run.assert_not_called()
        assert result["resume"] is True
        assert result["id"] == "existing-run"

    def test_resumes_partial_run(self):
        existing = {"id": "partial-run", "status": "partial"}
        crawl_run_repo = MagicMock()
        crawl_run_repo.get_today_run.return_value = existing

        country_status_repo = MagicMock()

        result = get_or_create_today_run(crawl_run_repo, country_status_repo)

        assert result["resume"] is True

    def test_creates_new_when_completed(self):
        existing = {"id": "old-run", "status": "completed"}
        crawl_run_repo = MagicMock()
        crawl_run_repo.get_today_run.return_value = existing
        crawl_run_repo.create_run.return_value = {"id": "new-run"}

        country_status_repo = MagicMock()

        result = get_or_create_today_run(crawl_run_repo, country_status_repo)

        crawl_run_repo.create_run.assert_called_once()
        assert result["resume"] is False


@pytest.mark.asyncio
async def test_orchestrator_runs_with_mocked_repos():
    """Test orchestrator flow with all dependencies mocked."""
    mock_radar = MagicMock()
    mock_radar.get_geolocations = AsyncMock(
        return_value=[
            {"code": "US", "name": "United States"},
        ]
    )
    mock_radar.get_top_domains = AsyncMock(
        return_value=[
            MagicMock(
                domain="rising-app.com",
                rank=1,
                pct_rank_change=200.0,
                categories=[],
            )
        ]
    )

    mock_domain_repo = MagicMock()
    mock_domain_repo.get_by_normalized_domain.return_value = None
    mock_domain_repo.upsert_domain.return_value = {
        "id": "domain-uuid",
        "normalized_domain": "rising-app.com",
    }

    mock_observation_repo = MagicMock()
    mock_observation_repo.insert_observation.return_value = {"id": "obs-uuid"}

    mock_crawl_repo = MagicMock()
    mock_crawl_repo.create_run.return_value = {"id": "run-uuid"}
    mock_crawl_repo.update_progress.return_value = {}
    mock_crawl_repo.complete_run.return_value = {"id": "run-uuid", "status": "completed"}

    mock_country_repo = MagicMock()
    mock_country_repo.upsert_country_status.return_value = {}

    orchestrator = CrawlOrchestrator(
        cloudflare_client=MagicMock(),
        llm_client=None,
        domain_repo=mock_domain_repo,
        observation_repo=mock_observation_repo,
        crawl_run_repo=mock_crawl_repo,
        country_status_repo=mock_country_repo,
        limit_per_country=50,
    )

    orchestrator._radar = mock_radar

    await orchestrator.run(
        run_date=date.today(),
        countries=[{"code": "US", "name": "United States"}],
    )

    # Two ranking types processed, domain is new each time (mock always returns None)
    assert mock_domain_repo.upsert_domain.call_count == 2
    # Two observations inserted (one per ranking type)
    assert mock_observation_repo.insert_observation.call_count == 2
