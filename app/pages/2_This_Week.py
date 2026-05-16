import sys
from pathlib import Path

import pandas as pd
import streamlit as st

project_root = Path(__file__).resolve().parent.parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from app.components.domain_table import render_domain_table
from app.components.filters import render_filters
from app.components.metrics_cards import render_metrics_cards
from app.data_loader import load_comments, load_stats
from src.config.constants import ReviewStatus
from src.db.repositories import CommentRepository, DomainRepository
from src.db.supabase_client import get_supabase_client

st.set_page_config(page_title="This Week", page_icon="📊", layout="wide")

st.title("Best Score This Week")

filters = render_filters()

stats = load_stats()
render_metrics_cards(
    {
        "countries_ran": stats.get("countries_completed", 0),
        "countries_total": stats.get("countries_total", 0),
        "new_domains": stats.get("new_domains_count", 0),
        "duplicates": stats.get("duplicate_domains_count", 0),
        "high_score_today": 0,
    }
)

st.divider()


def load_week_data(
    show_reviewed: bool = False,
    sort_by: str = "Score (desc)",
    min_score: int = 0,
) -> pd.DataFrame:
    try:
        client = get_supabase_client()
        query = client.table("v_domains_this_week").select("*")

        if not show_reviewed:
            query = query.eq("review_status", "pending")

        response = query.execute()

        if not response.data:
            return pd.DataFrame()

        df = pd.DataFrame(response.data)

        if "best_score_week" in df.columns:
            df = df[df["best_score_week"] >= min_score]

        if sort_by == "Score (desc)":
            df = df.sort_values("best_score_week", ascending=False)
        elif sort_by == "Score (asc)":
            df = df.sort_values("best_score_week", ascending=True)
        elif sort_by == "Newest":
            df = df.sort_values("first_seen_in_week", ascending=False)
        elif sort_by == "Country count":
            df = df.sort_values("countries_this_week", ascending=False)

        df["Site"] = df["display_url"].fillna("https://" + df["normalized_domain"])
        df["Summary"] = df["llm_summary"].fillna("No summary yet")
        df["Score"] = df["best_score_week"].fillna(0).astype(int)
        df["First seen"] = df["first_seen_in_week"]
        df["Last seen"] = df["last_seen_in_week"]
        df["Countries"] = df["countries_this_week"].fillna(0).astype(int)
        df["Observed"] = df["times_observed"].fillna(0).astype(int)
        df["Status"] = df["review_status"]
        df["Comments"] = df["comment_count"].fillna(0).astype(int)

        return df[
            [
                "id",
                "Site",
                "Summary",
                "Score",
                "First seen",
                "Last seen",
                "Countries",
                "Observed",
                "Status",
                "Comments",
            ]
        ]

    except Exception as e:
        st.error(f"Failed to load data: {e}")
        return pd.DataFrame()


df = load_week_data(
    show_reviewed=filters["show_reviewed"],
    sort_by=filters["sort_by"],
    min_score=filters["min_score"],
)

if not df.empty:
    comments_data = load_comments(df["id"].tolist())
else:
    comments_data = {}


def on_status_change(domain_id: str, new_status: str):
    repo = DomainRepository()
    review_status = ReviewStatus(new_status)
    repo.update_review_status(domain_id, review_status)
    st.rerun()


def on_add_comment(domain_id: str, author: str, message: str):
    repo = CommentRepository()
    repo.add_comment(domain_id, author, message)
    st.rerun()


render_domain_table(df, on_status_change=on_status_change, on_add_comment=on_add_comment, comments_data=comments_data)
