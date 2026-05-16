import pytest

from src.llm.schemas import LLMEnrichmentResult


def test_valid_result():
    result = LLMEnrichmentResult(
        summary="A test site.",
        category="AI",
        business_model="subscription",
        target_users="Developers",
        localization_angle="Romania",
        risk_notes="",
        novelty=3,
        idea_potential=4,
        confidence=3,
    )

    assert result.summary == "A test site."
    assert result.category == "AI"


def test_failed_result():
    result = LLMEnrichmentResult.failed(
        domain="example.com",
        error="HTTP timeout",
    )

    assert "LLM enrichment failed" in result.summary
    assert "HTTP timeout" in result.risk_notes
    assert result.novelty == 1
    assert result.idea_potential == 1


def test_invalid_score_too_low():
    with pytest.raises(Exception):
        LLMEnrichmentResult(
            summary="Test",
            category="AI",
            business_model="subscription",
            target_users="Devs",
            localization_angle="Romania",
            novelty=0,
            idea_potential=3,
            confidence=3,
        )


def test_invalid_score_too_high():
    with pytest.raises(Exception):
        LLMEnrichmentResult(
            summary="Test",
            category="AI",
            business_model="subscription",
            target_users="Devs",
            localization_angle="Romania",
            novelty=6,
            idea_potential=3,
            confidence=3,
        )


def test_empty_summary_rejected():
    with pytest.raises(Exception):
        LLMEnrichmentResult(
            summary="",
            category="AI",
            business_model="subscription",
            target_users="Devs",
            localization_angle="Romania",
            novelty=3,
            idea_potential=3,
            confidence=3,
        )
