from src.config.constants import (
    BASE_SCORE,
    KNOWN_GIANTS,
    RANKING_TYPE_BONUS,
    CrawlCountryStatus,
    CrawlRunStatus,
    RankingType,
    ReviewStatus,
)


def test_ranking_type_values():
    assert RankingType.TRENDING_RISE.value == "TRENDING_RISE"
    assert RankingType.TRENDING_STEADY.value == "TRENDING_STEADY"
    assert RankingType.POPULAR.value == "POPULAR"


def test_review_status_values():
    assert ReviewStatus.PENDING.value == "pending"
    assert ReviewStatus.OK.value == "ok"
    assert ReviewStatus.EXISTS.value == "exists"
    assert ReviewStatus.BAD.value == "bad"


def test_crawl_run_status_values():
    assert CrawlRunStatus.PENDING.value == "pending"
    assert CrawlRunStatus.RUNNING.value == "running"
    assert CrawlRunStatus.COMPLETED.value == "completed"
    assert CrawlRunStatus.FAILED.value == "failed"
    assert CrawlRunStatus.PARTIAL.value == "partial"


def test_crawl_country_status_values():
    assert CrawlCountryStatus.PENDING.value == "pending"
    assert CrawlCountryStatus.COMPLETED.value == "completed"


def test_known_giants_is_frozenset():
    assert isinstance(KNOWN_GIANTS, frozenset)
    assert "google.com" in KNOWN_GIANTS
    assert "youtube.com" in KNOWN_GIANTS


def test_base_score():
    assert BASE_SCORE == 20


def test_ranking_type_bonus():
    assert RANKING_TYPE_BONUS["TRENDING_RISE"] == 30
    assert RANKING_TYPE_BONUS["TRENDING_STEADY"] == 18
    assert RANKING_TYPE_BONUS["POPULAR"] == 5
