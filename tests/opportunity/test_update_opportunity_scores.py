import logging
from types import SimpleNamespace

import pytest

import src.opportunity.update_opportunity_scores as update_module
from src.opportunity.schemas import OpportunityScoreResult
from src.opportunity.update_opportunity_scores import (
    _update_opportunity_fields,
    score_single_domain,
    update_opportunity_scores,
)


def _valid_result(**overrides):
    data = {
        "opportunity_score": 72,
        "confidence": 80,
        "is_global_giant": False,
        "is_too_generic": False,
        "romania_market_fit": 4,
        "local_gap": 4,
        "buildability": 3,
        "monetization_clarity": 4,
        "novelty": 3,
        "trend_relevance": 4,
        "competition_saturation": 2,
        "complexity": 3,
        "regulatory_risk": 1,
        "recommended_category": "SaaS",
        "opportunity_type": "b2b_saas",
        "one_sentence_summary": "A focused SaaS opportunity.",
        "romania_adaptation_idea": "Adapt it for Romanian SMEs.",
        "why_it_scores_this_way": "It is practical and monetizable.",
        "red_flags": [],
        "suggested_mvp": "Build a narrow MVP for SMEs.",
    }
    data.update(overrides)
    return OpportunityScoreResult.model_validate(data)


class FakeDomainRepo:
    def __init__(self):
        self.updates = []

    def update_opportunity_fields(self, domain_id, update):
        self.updates.append((domain_id, update))
        return update


class FakeQuery:
    def __init__(self, rows):
        self.rows = rows
        self.filters = []

    def select(self, *_args, **_kwargs):
        return self

    def order(self, *_args, **_kwargs):
        return self

    def is_(self, column, value):
        self.filters.append(("is", column, value))
        return self

    def gte(self, column, value):
        self.filters.append(("gte", column, value))
        return self

    def range(self, *_args, **_kwargs):
        return self

    def execute(self):
        return SimpleNamespace(data=self.rows)


class FakeClient:
    def __init__(self, query):
        self.query = query

    def table(self, _table_name):
        return self.query


class FakeScorerForCommand:
    model = "test-model"
    validation_retries = 0
    client = SimpleNamespace(retry_counts={})

    def __init__(self, **_kwargs):
        pass

    async def close(self):
        pass


def _patch_command_dependencies(monkeypatch, tmp_path, query):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(update_module, "DomainRepository", lambda: SimpleNamespace(_client=FakeClient(query)))
    monkeypatch.setattr(update_module, "ObservationRepository", lambda: object())
    monkeypatch.setattr(
        update_module,
        "Settings",
        lambda: SimpleNamespace(lmstudio_base_url="http://test", lmstudio_model="test-model"),
    )
    monkeypatch.setattr(update_module, "OpportunityScorer", FakeScorerForCommand)


def test_update_opportunity_fields_falls_back_when_status_columns_are_missing():
    class Repo(FakeDomainRepo):
        def update_opportunity_fields(self, domain_id, update):
            self.updates.append((domain_id, update))
            if len(self.updates) == 1:
                raise Exception("column opportunity_score_status does not exist")
            return update

    repo = Repo()

    result = _update_opportunity_fields(
        repo,
        "domain-1",
        {
            "opportunity_score": 50,
            "opportunity_score_status": "failed",
            "opportunity_score_error": "rate limited",
        },
    )

    assert result == {"opportunity_score": 50}
    assert repo.updates[1][1] == {"opportunity_score": 50}


@pytest.mark.asyncio
async def test_only_missing_force_still_queries_missing_scores(monkeypatch, tmp_path):
    query = FakeQuery([])
    _patch_command_dependencies(monkeypatch, tmp_path, query)

    processed = await update_opportunity_scores(only_missing=True, force=True)

    assert processed == 0
    assert ("is", "opportunity_score", None) in query.filters


@pytest.mark.asyncio
async def test_only_missing_logs_force_hint_when_all_missing_rows_failed(monkeypatch, tmp_path, caplog):
    query = FakeQuery(
        [
            {"id": "domain-1", "normalized_domain": "example.com", "opportunity_score_status": "failed"},
            {"id": "domain-2", "normalized_domain": "example.org", "opportunity_score_status": "failed"},
        ]
    )
    _patch_command_dependencies(monkeypatch, tmp_path, query)
    caplog.set_level(logging.WARNING)

    processed = await update_opportunity_scores(only_missing=True, force=False)

    assert processed == 0
    assert "Run ./start-score --force to retry failed rows" in caplog.text


@pytest.mark.asyncio
async def test_score_single_domain_scores_without_homepage_when_fetch_misses(monkeypatch):
    domain_repo = FakeDomainRepo()
    stats = {}
    captured = {}

    async def fake_get_context(*args, **kwargs):
        return {
            "domain": "example.com",
            "display_url": "https://example.com",
            "trend_score": 12,
            "countries_observed": ["RO"],
            "ranking_types": ["trending_rise"],
            "best_rank": 5,
            "pct_rank_change": None,
            "first_seen_at": "2026-05-18T00:00:00+00:00",
            "existing_category": None,
            "existing_summary": None,
            "existing_llm_potential": None,
            "review_status": "pending",
            "romanian_signals": True,
        }

    async def fake_fetch_homepage_excerpt(url):
        captured["url"] = url
        return None

    class FakeScorer:
        model = "test-model"

        async def score_domain(self, context, homepage_excerpt=None):
            captured["homepage_excerpt"] = homepage_excerpt
            return _valid_result()

    monkeypatch.setattr("src.opportunity.update_opportunity_scores.get_domain_context", fake_get_context)
    monkeypatch.setattr("src.opportunity.update_opportunity_scores.fetch_homepage_excerpt", fake_fetch_homepage_excerpt)

    result = await score_single_domain(
        domain_repo=domain_repo,
        observation_repo=object(),
        scorer=FakeScorer(),
        domain_row={
            "id": "domain-1",
            "normalized_domain": "example.com",
            "display_url": "https://example.com",
            "review_status": "pending",
        },
        fetch_homepage=True,
        dry_run=False,
        stats=stats,
    )

    assert result["success"] is True
    assert captured == {"url": "https://example.com", "homepage_excerpt": None}
    assert stats["homepage_misses"] == 1
    assert domain_repo.updates[0][1]["opportunity_score_status"] == "scored"
