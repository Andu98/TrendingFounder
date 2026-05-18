"""Tests for global giant guardrails."""

from src.opportunity.update_opportunity_scores import is_known_global_giant, apply_giant_cap


def test_known_global_giants():
    giants = [
        "amazon.com", "google.com", "facebook.com", "youtube.com",
        "netflix.com", "booking.com", "airbnb.com", "microsoft.com",
        "apple.com", "tiktok.com", "github.com", "linkedin.com",
        "reddit.com", "spotify.com", "notion.so", "figma.com",
        "tesla.com", "nvidia.com",
    ]
    for domain in giants:
        assert is_known_global_giant(domain), f"{domain} should be a known giant"


def test_non_giants():
    non_giants = [
        "example.com", "startup.io", "localshop.ro", "niche-tool.com",
        "romania-saas.ro",
    ]
    for domain in non_giants:
        assert not is_known_global_giant(domain), f"{domain} should not be a known giant"


def test_case_insensitive():
    assert is_known_global_giant("AMAZON.COM")
    assert is_known_global_giant("Google.com")
    assert is_known_global_giant("FACEBOOK.COM")


def test_giant_cap_applies():
    assert apply_giant_cap("amazon.com", 80) == 20
    assert apply_giant_cap("google.com", 50) == 20
    assert apply_giant_cap("amazon.com", 15) == 15
    assert apply_giant_cap("amazon.com", 20) == 20


def test_non_giant_unchanged():
    assert apply_giant_cap("example.com", 80) == 80
    assert apply_giant_cap("startup.io", 50) == 50
    assert apply_giant_cap("niche.ro", 10) == 10
