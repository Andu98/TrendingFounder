from datetime import date
from pathlib import Path
from unittest.mock import MagicMock

import pandas as pd
from app import data_loader, streamlit_app
from app.components import filters


def _mock_rpc_client(rows: list[dict]):
    response = MagicMock()
    response.data = rows
    client = MagicMock()
    client.rpc.return_value.execute.return_value = response
    return client


def test_load_collected_data_calls_range_rpc(monkeypatch):
    rows = [
        {
            "id": "domain-1",
            "normalized_domain": "example.com",
            "display_url": "https://example.com",
            "llm_summary": "Example summary",
            "best_score_today": 91,
            "llm_category": "SaaS",
            "llm_business_model": "subscription",
            "review_status": "pending",
            "comment_count": 2,
            "countries_today": 3,
            "country_codes": ["DE", "RO", "US"],
            "ranking_types": ["popular", "trending_rise"],
            "first_seen_date": "2026-05-14",
            "first_seen_in_range": "2026-05-15",
            "last_seen_in_range": "2026-05-16",
            "times_observed": 4,
            "initial_score": 80,
            "total_count": 123,
        }
    ]
    client = _mock_rpc_client(rows)
    monkeypatch.setattr(data_loader, "get_supabase_client", lambda: client)

    df, total_count = data_loader.load_collected_data(
        show_reviewed=True,
        sort_by="Newest",
        search_query="example",
        status_filter="ok,exists",
        category_filter="SaaS",
        date_start=date(2026, 5, 15),
        date_end=date(2026, 5, 16),
        page=2,
        page_size=50,
    )

    rpc_name, rpc_params = client.rpc.call_args.args
    assert rpc_name == "get_domains_for_range"
    assert rpc_params == {
        "start_date": "2026-05-15",
        "end_date": "2026-05-16",
        "show_reviewed": True,
        "status_filter": "ok,exists",
        "category_filter": "SaaS",
        "search_query": "example",
        "sort_by": "Newest",
        "min_opportunity_score": 0,
        "min_opportunity_confidence": 0,
        "opportunity_type_filter": "All Types",
        "hide_global_giants": False,
        "page": 2,
        "page_size": 50,
    }
    assert total_count == 123
    assert df.iloc[0]["Domain"] == "example.com"
    assert df.iloc[0]["Score"] == 91
    assert df.iloc[0]["First country"] == "Germany"
    assert df.iloc[0]["Country Names"] == ["Germany", "Romania", "United States"]
    assert df.iloc[0]["First seen in range"] == "2026-05-15"
    assert df.iloc[0]["Last seen in range"] == "2026-05-16"
    assert df.iloc[0]["Times observed"] == 4


def test_load_collected_data_empty_response(monkeypatch):
    client = _mock_rpc_client([])
    monkeypatch.setattr(data_loader, "get_supabase_client", lambda: client)

    df, total_count = data_loader.load_collected_data()

    assert df.empty
    assert total_count == 0


def test_load_today_data_keeps_legacy_dataframe_shape(monkeypatch):
    captured = {}

    def fake_load_collected_data(**kwargs):
        captured.update(kwargs)
        return pd.DataFrame({"Score": [80, 20], "Domain": ["a.com", "b.com"]}), 2

    monkeypatch.setattr(data_loader, "load_collected_data", fake_load_collected_data)

    df = data_loader.load_today_data(min_score=50)

    assert captured["date_start"] == date.today()
    assert captured["date_end"] == date.today()
    assert captured["page"] == 1
    assert captured["page_size"] == 10_000
    assert df["Domain"].tolist() == ["a.com"]


def test_filter_signature_changes_for_range_and_page_size():
    filters = {
        "date_start": date(2026, 5, 16),
        "date_end": date(2026, 5, 16),
        "search_query": "",
        "status_filter": "All Statuses",
        "category_filter": "All Categories",
        "show_reviewed": True,
        "sort_by": "Score High → Low",
        "min_opportunity_score": 0,
        "min_opportunity_confidence": 0,
        "hide_global_giants": False,
        "opportunity_type_filter": "All Types",
    }

    same_day_signature = streamlit_app._filter_signature(filters, 50)
    filters["date_end"] = date(2026, 5, 20)

    assert streamlit_app._filter_signature(filters, 50) != same_day_signature
    assert streamlit_app._filter_signature(filters, 100) != streamlit_app._filter_signature(filters, 50)


def test_pending_review_status_updates_hide_reviewed_rows_until_refetch():
    df = pd.DataFrame(
        {
            "id": ["domain-1", "domain-2"],
            "Status": ["pending", "pending"],
            "Domain": ["one.test", "two.test"],
        }
    )

    visible_df = streamlit_app._apply_pending_review_status_updates(
        df,
        {"domain-1": "exists"},
        show_reviewed=False,
    )

    assert visible_df["id"].tolist() == ["domain-2"]


def test_status_change_clears_dashboard_cache_before_rerun(monkeypatch):
    executor = MagicMock()
    clear_dashboard_caches = MagicMock()
    rerun = MagicMock()

    monkeypatch.setattr(streamlit_app, "_STATUS_UPDATE_EXECUTOR", executor)
    monkeypatch.setattr(streamlit_app, "clear_dashboard_caches", clear_dashboard_caches)
    monkeypatch.setattr(streamlit_app.st, "session_state", {})
    monkeypatch.setattr(streamlit_app.st, "rerun", rerun)

    streamlit_app.on_status_change("domain-1", "exists")

    assert streamlit_app.st.session_state["_pending_domain_status_updates"] == {"domain-1": "exists"}
    executor.submit.assert_called_once_with(streamlit_app._persist_domain_status_change, "domain-1", "exists")
    clear_dashboard_caches.assert_not_called()
    rerun.assert_called_once_with()


def test_persist_domain_status_change_clears_dashboard_caches(monkeypatch):
    repo = MagicMock()
    clear_dashboard_caches = MagicMock()

    monkeypatch.setattr(streamlit_app, "DomainRepository", lambda: repo)
    monkeypatch.setattr(streamlit_app, "clear_dashboard_caches", clear_dashboard_caches)

    streamlit_app._persist_domain_status_change("domain-1", "exists")

    repo.update_review_status.assert_called_once_with("domain-1", streamlit_app.ReviewStatus("exists"))
    clear_dashboard_caches.assert_called_once_with()


def test_collected_data_render_prefers_snapshot_for_one_optimistic_refresh(monkeypatch):
    filters = {
        "search_query": "",
        "status_filter": "All Statuses",
        "category_filter": "All Categories",
        "show_reviewed": False,
        "sort_by": "Score High → Low",
        "date_start": date(2026, 5, 1),
        "date_end": date(2026, 5, 31),
        "min_opportunity_score": 0,
        "min_opportunity_confidence": 0,
        "hide_global_giants": False,
        "opportunity_type_filter": "All Types",
    }
    page = 1
    page_size = 50
    snapshot_df = pd.DataFrame({"id": ["domain-1"], "Status": ["pending"]})
    signature = streamlit_app._filter_signature(filters, page_size) + (page,)

    monkeypatch.setattr(
        streamlit_app.st,
        "session_state",
        {
            "_collected_data_snapshot": {"signature": signature, "df": snapshot_df, "total_count": 1},
            "_collected_optimistic_refresh": True,
        },
    )
    load_collected_data = MagicMock(side_effect=AssertionError("load_collected_data should not run"))
    monkeypatch.setattr(streamlit_app, "load_collected_data", load_collected_data)

    df, total_count = streamlit_app._load_collected_data_for_render(filters, page, page_size)

    assert total_count == 1
    assert df.equals(snapshot_df)
    load_collected_data.assert_not_called()


def test_confirmed_review_status_updates_are_pruned():
    df = pd.DataFrame(
        {
            "id": ["domain-1", "domain-2"],
            "Status": ["exists", "pending"],
        }
    )
    pending_updates = {"domain-1": "exists", "domain-2": "ok"}

    streamlit_app._prune_confirmed_review_status_updates(df, pending_updates)

    assert pending_updates == {"domain-2": "ok"}


def test_mark_github_repos_seen_marks_visible_repository_ids(monkeypatch):
    repo = MagicMock()
    repo.mark_seen_many.return_value = 2
    monkeypatch.setattr(data_loader, "GitHubRepositoryRepository", lambda: repo)
    monkeypatch.setattr(data_loader, "clear_github_caches", MagicMock())

    updated = data_loader.mark_github_repos_seen(["repo-1", "repo-2"])

    assert updated == 2
    repo.mark_seen_many.assert_called_once_with(["repo-1", "repo-2"])
    data_loader.clear_github_caches.assert_called_once_with()


def test_status_filter_from_checkbox_values():
    assert (
        filters._status_filter_from_values({"pending": True, "ok": True, "exists": True, "bad": True}) == "All Statuses"
    )
    assert (
        filters._status_filter_from_values({"pending": True, "ok": False, "exists": True, "bad": False})
        == "pending,exists"
    )
    assert (
        filters._status_filter_from_values({"pending": False, "ok": False, "exists": False, "bad": False}) == "__none__"
    )


def test_default_date_range_uses_full_current_month(monkeypatch):
    class FixedDate(date):
        @classmethod
        def today(cls):
            return cls(2026, 5, 20)

    monkeypatch.setattr(filters, "date", FixedDate)

    assert filters._default_date_range() == (date(2026, 5, 1), date(2026, 5, 31))


def test_session_date_range_defaults_to_full_current_month(monkeypatch):
    class FixedDate(date):
        @classmethod
        def today(cls):
            return cls(2026, 5, 20)

    monkeypatch.setattr(filters, "date", FixedDate)
    monkeypatch.setattr(streamlit_app.st, "session_state", {})

    assert streamlit_app._date_range_from_session() == (date(2026, 5, 1), date(2026, 5, 31))


def test_current_filter_values_defaults_show_reviewed_to_false(monkeypatch):
    monkeypatch.setattr(streamlit_app.st, "session_state", {})

    assert streamlit_app.current_filter_values()["show_reviewed"] is False


def test_range_rpc_newest_sort_uses_domain_first_seen_timestamp():
    sql = Path("supabase/schemas/002_views.sql").read_text()

    assert "dom.first_seen_at" in sql
    assert "p.sort_label = 'Newest' THEN counted.first_seen_at" in sql


def test_range_rpc_accepts_multiple_status_filters():
    sql = Path("supabase/schemas/002_views.sql").read_text()

    assert "p.status_filter = '__none__'" in sql
    assert "STRING_TO_ARRAY(p.status_filter, ',')" in sql
    assert "TRIM(status_value) IN ('pending', 'ok', 'exists', 'bad')" in sql


def test_range_rpc_score_sort_has_fallback_for_unscored_observations():
    sql = Path("supabase/schemas/002_views.sql").read_text()

    assert "COALESCE(\n            MAX(obs.observation_score)" in sql
    assert "WHEN 'trending_rise' THEN 80" in sql
    assert "WHEN obs.rank <= 10 THEN 25" in sql
    assert "dom.latest_best_score" in sql
