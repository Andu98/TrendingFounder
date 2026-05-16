from src.llm.prompts import SYSTEM_PROMPT, build_enrichment_prompt


def test_system_prompt_exists():
    assert SYSTEM_PROMPT is not None
    assert "JSON" in SYSTEM_PROMPT
    assert "Category" in SYSTEM_PROMPT


def test_build_prompt_minimal():
    prompt = build_enrichment_prompt(domain="example.com")
    assert "example.com" in prompt
    assert "JSON" in prompt


def test_build_prompt_with_all_fields():
    prompt = build_enrichment_prompt(
        domain="example.com",
        title="Example Site",
        meta_description="A great site",
        categories=[{"name": "AI"}, {"name": "SaaS"}],
        country_code="US",
        ranking_type="trending_rise",
        rank=1,
        pct_rank_change=200.0,
        homepage_snippet="Welcome to our site",
    )

    assert "example.com" in prompt
    assert "Example Site" in prompt
    assert "A great site" in prompt
    assert "AI, SaaS" in prompt
    assert "US" in prompt
    assert "trending_rise" in prompt
    assert "Rank: 1" in prompt
    assert "200.0" in prompt
    assert "Welcome to our site" in prompt


def test_build_prompt_truncates_snippet():
    long_snippet = "x" * 10000
    prompt = build_enrichment_prompt(
        domain="example.com",
        homepage_snippet=long_snippet,
    )

    assert len(prompt) < 15000
