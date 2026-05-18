"""Tests for opportunity prompt builder."""

from src.opportunity.prompt import build_opportunity_prompt


def test_prompt_includes_all_fields():
    prompt = build_opportunity_prompt(
        domain="example.com",
        display_url="https://example.com",
        trend_score=65.0,
        countries_observed=["US", "RO"],
        ranking_types=["trending_rise"],
        best_rank=15,
        pct_rank_change=12.5,
        first_seen_at="2025-05-01",
        existing_category="SaaS",
        existing_summary="A SaaS tool",
        existing_llm_potential=7,
        review_status="pending",
        romanian_signals=True,
    )

    assert "example.com" in prompt
    assert "https://example.com" in prompt
    assert "65.0" in prompt
    assert "US" in prompt
    assert "RO" in prompt
    assert "trending_rise" in prompt
    assert "15" in prompt
    assert "12.5" in prompt
    assert "2025-05-01" in prompt
    assert "SaaS" in prompt
    assert "A SaaS tool" in prompt
    assert "pending" in prompt
    assert "True" in prompt


def test_prompt_handles_none_values():
    prompt = build_opportunity_prompt(
        domain="test.com",
        display_url="https://test.com",
        trend_score=0.0,
        countries_observed=[],
        ranking_types=[],
        best_rank=0,
        pct_rank_change=None,
        first_seen_at="",
        existing_category=None,
        existing_summary=None,
        existing_llm_potential=None,
        review_status="pending",
        romanian_signals=False,
    )

    assert "None" in prompt
    assert "False" in prompt


def test_prompt_includes_homepage_excerpt():
    prompt = build_opportunity_prompt(
        domain="test.com",
        display_url="https://test.com",
        trend_score=50.0,
        countries_observed=["US"],
        ranking_types=["trending_rise"],
        best_rank=20,
        pct_rank_change=5.0,
        first_seen_at="2025-05-01",
        existing_category=None,
        existing_summary=None,
        existing_llm_potential=None,
        review_status="pending",
        romanian_signals=False,
        homepage_excerpt="Title: Test Site\nDescription: A test site.",
    )

    assert "Test Site" in prompt
    assert "A test site." in prompt


def test_prompt_includes_scoring_guidance():
    prompt = build_opportunity_prompt(
        domain="test.com",
        display_url="https://test.com",
        trend_score=50.0,
        countries_observed=["US"],
        ranking_types=["trending_rise"],
        best_rank=20,
        pct_rank_change=5.0,
        first_seen_at="2025-05-01",
        existing_category=None,
        existing_summary=None,
        existing_llm_potential=None,
        review_status="pending",
        romanian_signals=False,
    )

    assert "Romanian market" in prompt or "Romania" in prompt
    assert "opportunity_score" in prompt
    assert "confidence" in prompt
    assert "0-10:" in prompt
    assert "86-100:" in prompt
