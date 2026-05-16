from datetime import date, timedelta

from src.domains.scoring import ScoreBreakdown, score_observation


class TestScoreBreakdown:
    def test_total_is_sum_of_parts(self):
        b = ScoreBreakdown(
            base=20,
            ranking_type=30,
            rank=20,
            pct_rank_change=10,
            multi_country=4,
            category=15,
            novelty=20,
            llm_potential=10,
            known_giant=0,
            already_reviewed=0,
        )
        assert b.total == 129

    def test_details_returns_all_keys(self):
        b = ScoreBreakdown(base=20, ranking_type=30)
        details = b.details()
        assert "total" in details
        assert details["total"] == 50


class TestScoreObservation:
    def test_base_score(self):
        result = score_observation(
            ranking_type="trending_rise",
            rank=50,
        )
        assert result.base == 20

    def test_ranking_type_bonus_rise(self):
        result = score_observation(
            ranking_type="trending_rise",
            rank=50,
        )
        assert result.ranking_type == 30

    def test_ranking_type_bonus_steady(self):
        result = score_observation(
            ranking_type="trending_steady",
            rank=50,
        )
        assert result.ranking_type == 18

    def test_ranking_type_bonus_popular(self):
        result = score_observation(
            ranking_type="popular",
            rank=50,
        )
        assert result.ranking_type == 5

    def test_rank_bonus_top_10(self):
        result = score_observation(
            ranking_type="trending_rise",
            rank=5,
        )
        assert result.rank == 20

    def test_rank_bonus_11_to_25(self):
        result = score_observation(
            ranking_type="trending_rise",
            rank=20,
        )
        assert result.rank == 12

    def test_rank_bonus_26_to_50(self):
        result = score_observation(
            ranking_type="trending_rise",
            rank=40,
        )
        assert result.rank == 7

    def test_rank_bonus_51_to_100(self):
        result = score_observation(
            ranking_type="trending_rise",
            rank=75,
        )
        assert result.rank == 3

    def test_rank_bonus_out_of_range(self):
        result = score_observation(
            ranking_type="trending_rise",
            rank=200,
        )
        assert result.rank == 0

    def test_pct_rank_change_bonus(self):
        result = score_observation(
            ranking_type="trending_rise",
            rank=50,
            pct_rank_change=100.0,
        )
        assert result.pct_rank_change == 20

    def test_pct_rank_change_bonus_capped(self):
        result = score_observation(
            ranking_type="trending_rise",
            rank=50,
            pct_rank_change=500.0,
        )
        assert result.pct_rank_change == 20

    def test_pct_rank_change_none(self):
        result = score_observation(
            ranking_type="popular",
            rank=50,
            pct_rank_change=None,
        )
        assert result.pct_rank_change == 0

    def test_multi_country_bonus(self):
        result = score_observation(
            ranking_type="trending_rise",
            rank=50,
            countries_seen_today=5,
        )
        assert result.multi_country == 8

    def test_multi_country_bonus_capped(self):
        result = score_observation(
            ranking_type="trending_rise",
            rank=50,
            countries_seen_today=20,
        )
        assert result.multi_country == 20

    def test_multi_country_single_country(self):
        result = score_observation(
            ranking_type="trending_rise",
            rank=50,
            countries_seen_today=1,
        )
        assert result.multi_country == 0

    def test_category_bonus_ai(self):
        result = score_observation(
            ranking_type="trending_rise",
            rank=50,
            llm_category="AI",
        )
        assert result.category == 15

    def test_category_bonus_ecommerce(self):
        result = score_observation(
            ranking_type="trending_rise",
            rank=50,
            llm_category="Ecommerce",
        )
        assert result.category == 10

    def test_category_penalty_adult(self):
        result = score_observation(
            ranking_type="trending_rise",
            rank=50,
            llm_category="Adult",
        )
        assert result.category == -30

    def test_category_unknown_zero(self):
        result = score_observation(
            ranking_type="trending_rise",
            rank=50,
            llm_category="UnknownCategory",
        )
        assert result.category == 0

    def test_novelty_first_seen_today(self):
        result = score_observation(
            ranking_type="trending_rise",
            rank=50,
            first_seen_date=date.today(),
        )
        assert result.novelty == 20

    def test_novelty_first_seen_this_week(self):
        three_days_ago = date.today() - timedelta(days=3)
        result = score_observation(
            ranking_type="trending_rise",
            rank=50,
            first_seen_date=three_days_ago,
        )
        assert result.novelty == 8

    def test_novelty_older_than_week(self):
        ten_days_ago = date.today() - timedelta(days=10)
        result = score_observation(
            ranking_type="trending_rise",
            rank=50,
            first_seen_date=ten_days_ago,
        )
        assert result.novelty == 0

    def test_llm_potential_bonus(self):
        result = score_observation(
            ranking_type="trending_rise",
            rank=50,
            llm_idea_potential=5,
        )
        assert result.llm_potential == 20

    def test_llm_potential_bonus_mid(self):
        result = score_observation(
            ranking_type="trending_rise",
            rank=50,
            llm_idea_potential=3,
        )
        assert result.llm_potential == 10

    def test_llm_potential_minimum(self):
        result = score_observation(
            ranking_type="trending_rise",
            rank=50,
            llm_idea_potential=1,
        )
        assert result.llm_potential == 0

    def test_known_giant_penalty(self):
        result = score_observation(
            ranking_type="trending_rise",
            rank=1,
            normalized_domain="google.com",
        )
        assert result.known_giant == -50

    def test_already_reviewed_penalty(self):
        result = score_observation(
            ranking_type="trending_rise",
            rank=50,
            review_status="ok",
        )
        assert result.already_reviewed == -100

    def test_pending_no_penalty(self):
        result = score_observation(
            ranking_type="trending_rise",
            rank=50,
            review_status="pending",
        )
        assert result.already_reviewed == 0

    def test_full_score_calculation(self):
        result = score_observation(
            ranking_type="trending_rise",
            rank=5,
            pct_rank_change=100.0,
            countries_seen_today=3,
            llm_category="AI",
            llm_idea_potential=4,
            first_seen_date=date.today(),
            review_status="pending",
            normalized_domain="new-startup.io",
        )

        assert result.base == 20
        assert result.ranking_type == 30
        assert result.rank == 20
        assert result.pct_rank_change == 20
        assert result.multi_country == 4
        assert result.category == 15
        assert result.novelty == 20
        assert result.llm_potential == 15
        assert result.known_giant == 0
        assert result.already_reviewed == 0
        assert result.total == 144
