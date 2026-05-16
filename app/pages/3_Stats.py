import sys
from pathlib import Path

import pandas as pd
import streamlit as st

project_root = Path(__file__).resolve().parent.parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from app.components.metrics_cards import render_metrics_cards, render_progress_bar
from app.data_loader import load_high_score_count, load_stats
from src.config.constants import COUNTRY_CODES
from src.db.supabase_client import get_supabase_client

st.set_page_config(page_title="Stats", page_icon="📈", layout="wide")

st.title("Crawl Stats")


def load_country_progress():
    try:
        client = get_supabase_client()
        response = client.table("v_crawl_country_progress").select("*").execute()
        if response.data:
            return pd.DataFrame(response.data)
    except Exception:
        pass
    return pd.DataFrame()


def country_display_name(row: pd.Series) -> str:
    country_name_value = row.get("country_name")
    country_name = "" if pd.isna(country_name_value) else str(country_name_value).strip()
    if country_name:
        return country_name
    country_code_value = row.get("country_code")
    country_code = "" if pd.isna(country_code_value) else str(country_code_value).strip()
    return COUNTRY_CODES.get(country_code.upper(), country_code)


stats = load_stats()
country_df = load_country_progress()

render_metrics_cards(
    {
        "countries_ran": stats.get("countries_completed", 0),
        "countries_total": stats.get("countries_total", 0),
        "new_domains": stats.get("new_domains_count", 0),
        "duplicates": stats.get("duplicate_domains_count", 0),
        "llm_processed": stats.get("llm_processed_count", 0),
        "high_score_today": load_high_score_count(),
        "reviewed_today": 0,
    }
)

st.divider()

st.subheader("Daily Crawl Progress")
render_progress_bar(
    stats.get("countries_completed", 0),
    stats.get("countries_total", 0),
)

if stats.get("status"):
    st.caption(f"Status: {stats['status']}")

st.divider()

st.subheader("Today's Crawl Status by Country")

if country_df.empty:
    st.info("No crawl data available for today.")
else:
    country_df["country_display_name"] = country_df.apply(country_display_name, axis=1)
    display_cols = {
        "country_display_name": "Country",
        "country_status": "Status",
        "items_found": "Items found",
        "new_domains": "New",
        "duplicate_domains": "Duplicates",
        "error_message": "Error",
    }
    country_df = country_df.rename(columns=display_cols)
    country_df = country_df[list(display_cols.values())]

    st.dataframe(country_df, use_container_width=True, hide_index=True)
