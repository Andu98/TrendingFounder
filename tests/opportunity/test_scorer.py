import pytest
from pydantic import ValidationError

from src.opportunity.scorer import OpportunityScorer


def _valid_response(**overrides):
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
    return data


@pytest.mark.asyncio
async def test_scorer_uses_json_schema_call(monkeypatch):
    scorer = OpportunityScorer(model="test-model")
    captured = {}

    async def fake_call_json_schema(**kwargs):
        captured.update(kwargs)
        return _valid_response()

    monkeypatch.setattr(scorer.client, "call_json_schema", fake_call_json_schema)

    result = await scorer.score_domain(
        {
            "domain": "example.com",
            "display_url": "https://example.com",
            "trend_score": 50,
            "countries_observed": ["RO"],
            "ranking_types": ["trending_rise"],
            "best_rank": 10,
            "review_status": "pending",
            "romanian_signals": True,
        },
        homepage_excerpt=None,
    )

    assert result.opportunity_score == 72
    assert captured["schema_name"] == "OpportunityScoreResult"
    assert captured["schema"]["additionalProperties"] is False


@pytest.mark.asyncio
async def test_scorer_retries_validation_once(monkeypatch):
    scorer = OpportunityScorer(model="test-model")
    calls = []

    async def fake_call_json_schema(**kwargs):
        calls.append(kwargs["prompt"])
        if len(calls) == 1:
            return _valid_response(opportunity_score=999)
        return _valid_response(opportunity_score=40)

    monkeypatch.setattr(scorer.client, "call_json_schema", fake_call_json_schema)

    result = await scorer.score_domain({"domain": "example.com", "display_url": "https://example.com"})

    assert result.opportunity_score == 40
    assert scorer.validation_retries == 1
    assert "Every required string field must contain a string" in calls[1]


@pytest.mark.asyncio
async def test_scorer_does_not_swallow_second_validation_failure(monkeypatch):
    scorer = OpportunityScorer(model="test-model")

    async def fake_call_json_schema(**kwargs):
        return _valid_response(opportunity_score=999)

    monkeypatch.setattr(scorer.client, "call_json_schema", fake_call_json_schema)

    with pytest.raises(ValidationError):
        await scorer.score_domain({"domain": "example.com", "display_url": "https://example.com"})
