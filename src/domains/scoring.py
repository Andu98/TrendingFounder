from dataclasses import dataclass
from datetime import date

from src.config.constants import (
    ALREADY_REVIEWED_PENALTY,
    BASE_SCORE,
    CATEGORY_BONUS,
    KNOWN_GIANT_PENALTY,
    MULTI_COUNTRY_MAX,
    MULTI_COUNTRY_PER_COUNTRY,
    NOVELTY_FIRST_SEEN_TODAY,
    NOVELTY_FIRST_SEEN_WEEK,
    PCT_RANK_CHANGE_DIVISOR,
    PCT_RANK_CHANGE_MAX,
    RANK_BONUS_TIERS,
    RANKING_TYPE_BONUS,
)
from src.domains.normalize import is_known_giant


@dataclass
class ScoreBreakdown:
    base: int = 0
    ranking_type: int = 0
    rank: int = 0
    pct_rank_change: int = 0
    multi_country: int = 0
    category: int = 0
    novelty: int = 0
    llm_potential: int = 0
    known_giant: int = 0
    already_reviewed: int = 0

    @property
    def total(self) -> int:
        return (
            self.base
            + self.ranking_type
            + self.rank
            + self.pct_rank_change
            + self.multi_country
            + self.category
            + self.novelty
            + self.llm_potential
            + self.known_giant
            + self.already_reviewed
        )

    def details(self) -> dict[str, int]:
        return {
            "base": self.base,
            "ranking_type": self.ranking_type,
            "rank": self.rank,
            "pct_rank_change": self.pct_rank_change,
            "multi_country": self.multi_country,
            "category": self.category,
            "novelty": self.novelty,
            "llm_potential": self.llm_potential,
            "known_giant": self.known_giant,
            "already_reviewed": self.already_reviewed,
            "total": self.total,
        }


def score_observation(
    ranking_type: str,
    rank: int,
    pct_rank_change: float | None = None,
    countries_seen_today: int = 1,
    llm_category: str | None = None,
    llm_idea_potential: int | None = None,
    first_seen_date: date | None = None,
    review_status: str = "pending",
    normalized_domain: str = "",
) -> ScoreBreakdown:
    """Calculate the observation score with a full breakdown.

    Formula from PLAN.md §10.1:
        score = base + ranking_type + rank + pct_rank_change
              + multi_country + category + novelty + llm_potential
              - known_giant - already_reviewed
    """
    breakdown = ScoreBreakdown()

    breakdown.base = BASE_SCORE

    breakdown.ranking_type = RANKING_TYPE_BONUS.get(ranking_type.upper(), 0)

    for (low, high), bonus in RANK_BONUS_TIERS:
        if low <= rank <= high:
            breakdown.rank = bonus
            break

    if pct_rank_change is not None:
        breakdown.pct_rank_change = min(PCT_RANK_CHANGE_MAX, int(pct_rank_change / PCT_RANK_CHANGE_DIVISOR))

    if countries_seen_today > 1:
        breakdown.multi_country = min(
            MULTI_COUNTRY_MAX,
            (countries_seen_today - 1) * MULTI_COUNTRY_PER_COUNTRY,
        )

    if llm_category:
        breakdown.category = CATEGORY_BONUS.get(llm_category, 0)

    if first_seen_date:
        today = date.today()
        if first_seen_date == today:
            breakdown.novelty = NOVELTY_FIRST_SEEN_TODAY
        elif (today - first_seen_date).days <= 7:
            breakdown.novelty = NOVELTY_FIRST_SEEN_WEEK

    if llm_idea_potential is not None:
        breakdown.llm_potential = (llm_idea_potential - 1) * 5

    if is_known_giant(normalized_domain):
        breakdown.known_giant = KNOWN_GIANT_PENALTY

    if review_status in ("ok", "exists", "bad"):
        breakdown.already_reviewed = ALREADY_REVIEWED_PENALTY

    return breakdown
