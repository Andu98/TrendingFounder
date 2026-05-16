from datetime import date
from unittest.mock import MagicMock

from src.domains.dedupe import dedupe_and_insert


def _mock_repo(existing_domain: dict | None = None):
    domain_repo = MagicMock()
    domain_repo.get_by_normalized_domain.return_value = existing_domain

    if existing_domain:
        domain_repo.upsert_domain.return_value = existing_domain
    else:
        domain_repo.upsert_domain.return_value = {
            "id": "new-domain-uuid",
            "normalized_domain": "example.com",
        }

    observation_repo = MagicMock()
    observation_repo.insert_observation.return_value = {"id": "obs-uuid"}

    return domain_repo, observation_repo


class TestDedupeAndInsert:
    def test_new_domain_creates_domain_and_observation(self):
        domain_repo, observation_repo = _mock_repo(existing_domain=None)

        result = dedupe_and_insert(
            domain_repo=domain_repo,
            observation_repo=observation_repo,
            raw_domain="https://www.Example.com/path",
            crawl_run_id="run-uuid",
            observed_date=date.today(),
            country_code="US",
            country_name="United States",
            ranking_type="trending_rise",
            rank=1,
            pct_rank_change=200.0,
        )

        assert result.is_new is True
        assert result.normalized_domain == "example.com"
        assert result.domain_id == "new-domain-uuid"

        domain_repo.upsert_domain.assert_called_once()
        observation_repo.insert_observation.assert_called_once()

    def test_existing_domain_skips_upsert_but_inserts_observation(self):
        existing = {"id": "existing-uuid", "normalized_domain": "example.com"}
        domain_repo, observation_repo = _mock_repo(existing_domain=existing)

        result = dedupe_and_insert(
            domain_repo=domain_repo,
            observation_repo=observation_repo,
            raw_domain="example.com",
            crawl_run_id="run-uuid",
            observed_date=date.today(),
            country_code="DE",
            country_name="Germany",
            ranking_type="trending_steady",
            rank=5,
        )

        assert result.is_new is False
        assert result.normalized_domain == "example.com"
        assert result.domain_id == "existing-uuid"

        domain_repo.upsert_domain.assert_not_called()
        observation_repo.insert_observation.assert_called_once()

    def test_same_domain_different_country_creates_new_observation(self):
        existing = {"id": "existing-uuid", "normalized_domain": "example.com"}
        domain_repo, observation_repo = _mock_repo(existing_domain=existing)

        dedupe_and_insert(
            domain_repo=domain_repo,
            observation_repo=observation_repo,
            raw_domain="example.com",
            crawl_run_id="run-uuid",
            observed_date=date.today(),
            country_code="RO",
            country_name="Romania",
            ranking_type="trending_rise",
            rank=10,
        )

        call_kwargs = observation_repo.insert_observation.call_args.kwargs
        assert call_kwargs["country_code"] == "RO"
        assert call_kwargs["ranking_type"] == "trending_rise"
