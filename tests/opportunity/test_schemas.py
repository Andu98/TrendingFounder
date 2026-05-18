"""Tests for opportunity scoring schemas."""

import pytest

from src.opportunity.schemas import OpportunityScoreResult


def test_valid_result():
    result = OpportunityScoreResult(
        opportunity_score=75,
        confidence=80,
        is_global_giant=False,
        is_too_generic=False,
        romania_market_fit=4,
        local_gap=3,
        buildability=4,
        monetization_clarity=3,
        novelty=4,
        trend_relevance=3,
        competition_saturation=2,
        complexity=3,
        regulatory_risk=1,
        recommended_category="SaaS",
        opportunity_type="b2b_saas",
        one_sentence_summary="A B2B SaaS tool for invoicing.",
        romania_adaptation_idea="Localize for Romanian SMEs with ANAF integration.",
        why_it_scores_this_way="Strong B2B demand, low competition locally.",
        red_flags=["Requires ANAF API access"],
        suggested_mvp="Simple invoicing dashboard with Romanian tax rules.",
    )

    assert result.opportunity_score == 75
    assert result.confidence == 80
    assert result.opportunity_type == "b2b_saas"


def test_score_bounds():
    with pytest.raises(Exception):
        OpportunityScoreResult(
            opportunity_score=-1,
            confidence=50,
            is_global_giant=False,
            is_too_generic=False,
            romania_market_fit=3,
            local_gap=3,
            buildability=3,
            monetization_clarity=3,
            novelty=3,
            trend_relevance=3,
            competition_saturation=3,
            complexity=3,
            regulatory_risk=3,
            recommended_category="Test",
            opportunity_type="b2b_saas",
            one_sentence_summary="Test",
            romania_adaptation_idea="Test",
            why_it_scores_this_way="Test",
            suggested_mvp="Test",
        )

    with pytest.raises(Exception):
        OpportunityScoreResult(
            opportunity_score=101,
            confidence=50,
            is_global_giant=False,
            is_too_generic=False,
            romania_market_fit=3,
            local_gap=3,
            buildability=3,
            monetization_clarity=3,
            novelty=3,
            trend_relevance=3,
            competition_saturation=3,
            complexity=3,
            regulatory_risk=3,
            recommended_category="Test",
            opportunity_type="b2b_saas",
            one_sentence_summary="Test",
            romania_adaptation_idea="Test",
            why_it_scores_this_way="Test",
            suggested_mvp="Test",
        )


def test_dimension_bounds():
    with pytest.raises(Exception):
        OpportunityScoreResult(
            opportunity_score=50,
            confidence=50,
            is_global_giant=False,
            is_too_generic=False,
            romania_market_fit=0,
            local_gap=3,
            buildability=3,
            monetization_clarity=3,
            novelty=3,
            trend_relevance=3,
            competition_saturation=3,
            complexity=3,
            regulatory_risk=3,
            recommended_category="Test",
            opportunity_type="b2b_saas",
            one_sentence_summary="Test",
            romania_adaptation_idea="Test",
            why_it_scores_this_way="Test",
            suggested_mvp="Test",
        )

    with pytest.raises(Exception):
        OpportunityScoreResult(
            opportunity_score=50,
            confidence=50,
            is_global_giant=False,
            is_too_generic=False,
            romania_market_fit=6,
            local_gap=3,
            buildability=3,
            monetization_clarity=3,
            novelty=3,
            trend_relevance=3,
            competition_saturation=3,
            complexity=3,
            regulatory_risk=3,
            recommended_category="Test",
            opportunity_type="b2b_saas",
            one_sentence_summary="Test",
            romania_adaptation_idea="Test",
            why_it_scores_this_way="Test",
            suggested_mvp="Test",
        )


def test_invalid_opportunity_type():
    """Empty or invalid types are normalized to 'other'."""
    result = OpportunityScoreResult(
        opportunity_score=50,
        confidence=50,
        is_global_giant=False,
        is_too_generic=False,
        romania_market_fit=3,
        local_gap=3,
        buildability=3,
        monetization_clarity=3,
        novelty=3,
        trend_relevance=3,
        competition_saturation=3,
        complexity=3,
        regulatory_risk=3,
        recommended_category="Test",
        opportunity_type="",
        one_sentence_summary="Test",
        romania_adaptation_idea="Test",
        why_it_scores_this_way="Test",
        suggested_mvp="Test",
    )
    assert result.opportunity_type == "other"


def test_all_valid_opportunity_types():
    valid_types = [
        "local_marketplace", "b2b_saas", "consumer_app", "vertical_saas",
        "content_platform", "ecommerce_tool", "education_tool",
        "healthcare_tool", "logistics_tool", "other",
    ]
    for opp_type in valid_types:
        result = OpportunityScoreResult(
            opportunity_score=50,
            confidence=50,
            is_global_giant=False,
            is_too_generic=False,
            romania_market_fit=3,
            local_gap=3,
            buildability=3,
            monetization_clarity=3,
            novelty=3,
            trend_relevance=3,
            competition_saturation=3,
            complexity=3,
            regulatory_risk=3,
            recommended_category="Test",
            opportunity_type=opp_type,
            one_sentence_summary="Test",
            romania_adaptation_idea="Test",
            why_it_scores_this_way="Test",
            suggested_mvp="Test",
        )
        assert result.opportunity_type == opp_type


def test_opportunity_type_normalization():
    """Test that invalid types are normalized to 'other'."""
    for invalid in ["", "string", "unknown", "N/A", "none", "  "]:
        result = OpportunityScoreResult(
            opportunity_score=50,
            confidence=50,
            is_global_giant=False,
            is_too_generic=False,
            romania_market_fit=3,
            local_gap=3,
            buildability=3,
            monetization_clarity=3,
            novelty=3,
            trend_relevance=3,
            competition_saturation=3,
            complexity=3,
            regulatory_risk=3,
            recommended_category="Test",
            opportunity_type=invalid,
            one_sentence_summary="Test",
            romania_adaptation_idea="Test",
            why_it_scores_this_way="Test",
            suggested_mvp="Test",
        )
        assert result.opportunity_type == "other"


def test_empty_red_flags_allowed():
    result = OpportunityScoreResult(
        opportunity_score=50,
        confidence=50,
        is_global_giant=False,
        is_too_generic=False,
        romania_market_fit=3,
        local_gap=3,
        buildability=3,
        monetization_clarity=3,
        novelty=3,
        trend_relevance=3,
        competition_saturation=3,
        complexity=3,
        regulatory_risk=3,
        recommended_category="Test",
        opportunity_type="b2b_saas",
        one_sentence_summary="Test",
        romania_adaptation_idea="Test",
        why_it_scores_this_way="Test",
        suggested_mvp="Test",
    )
    assert result.red_flags == []


def test_model_dump():
    result = OpportunityScoreResult(
        opportunity_score=60,
        confidence=70,
        is_global_giant=False,
        is_too_generic=False,
        romania_market_fit=4,
        local_gap=3,
        buildability=4,
        monetization_clarity=3,
        novelty=3,
        trend_relevance=3,
        competition_saturation=2,
        complexity=3,
        regulatory_risk=1,
        recommended_category="Marketplace",
        opportunity_type="local_marketplace",
        one_sentence_summary="Local marketplace.",
        romania_adaptation_idea="Adapt for Romania.",
        why_it_scores_this_way="Good opportunity.",
        red_flags=["Competition"],
        suggested_mvp="MVP description.",
    )

    dump = result.model_dump()
    assert dump["opportunity_score"] == 60
    assert dump["recommended_category"] == "Marketplace"
    assert dump["red_flags"] == ["Competition"]
