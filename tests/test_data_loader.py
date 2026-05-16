from datetime import date
from unittest.mock import MagicMock

import pandas as pd
from app import data_loader, streamlit_app


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
    monkeypatch.setattr(data_loader, "_enrich_domain_details", lambda df: df)

    df, total_count = data_loader.load_collected_data(
        show_reviewed=True,
        sort_by="Newest",
        search_query="example",
        status_filter="ok",
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
        "status_filter": "ok",
        "category_filter": "SaaS",
        "search_query": "example",
        "sort_by": "Newest",
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
    }

    same_day_signature = streamlit_app._filter_signature(filters, 50)
    filters["date_end"] = date(2026, 5, 20)

    assert streamlit_app._filter_signature(filters, 50) != same_day_signature
    assert streamlit_app._filter_signature(filters, 100) != streamlit_app._filter_signature(filters, 50)
