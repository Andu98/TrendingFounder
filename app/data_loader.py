import pandas as pd
import streamlit as st

from src.db.repositories import CrawlRunRepository
from src.db.supabase_client import get_supabase_client


def load_today_data(
    show_reviewed: bool = False,
    sort_by: str = "Score (desc)",
    min_score: int = 0,
) -> pd.DataFrame:
    """Load today's domains from Supabase view."""
    try:
        client = get_supabase_client()
        query = client.table("v_domains_today").select("*")

        if not show_reviewed:
            query = query.eq("review_status", "pending")

        response = query.execute()

        if not response.data:
            return pd.DataFrame()

        df = pd.DataFrame(response.data)

        # Filter by min score
        if "best_score_today" in df.columns:
            df = df[df["best_score_today"] >= min_score]

        # Sort
        if sort_by == "Score (desc)":
            df = df.sort_values("best_score_today", ascending=False)
        elif sort_by == "Score (asc)":
            df = df.sort_values("best_score_today", ascending=True)
        elif sort_by == "Newest":
            df = df.sort_values("first_seen_date", ascending=False)
        elif sort_by == "Country count":
            df = df.sort_values("countries_today", ascending=False)

        # Format for display
        df["Site"] = df["display_url"].fillna("https://" + df["normalized_domain"])
        df["Summary"] = df["llm_summary"].fillna("No summary yet")
        df["Score"] = df["best_score_today"].fillna(0).astype(int)
        df["First country"] = df.get("first_country_code", "")
        df["Countries"] = df["countries_today"].fillna(0).astype(int)
        df["Ranking types"] = df["ranking_types"].apply(lambda x: ", ".join(x) if isinstance(x, list) else str(x))
        df["Status"] = df["review_status"]
        df["Comments"] = df["comment_count"].fillna(0).astype(int)

        return df[
            [
                "id",
                "Site",
                "Summary",
                "Score",
                "First country",
                "Countries",
                "Ranking types",
                "Status",
                "Comments",
            ]
        ]

    except Exception as e:
        st.error(f"Failed to load data: {e}")
        return pd.DataFrame()


def load_stats() -> dict:
    """Load crawl stats."""
    try:
        repo = CrawlRunRepository()
        run = repo.get_today_run()
        if not run:
            return {}
        return run
    except Exception:
        return {}


def load_comments(domain_ids: list[str]) -> dict[str, list[dict]]:
    """Load comments for a list of domain IDs. Returns dict of domain_id -> [comments]."""
    try:
        client = get_supabase_client()
        response = client.table("domain_comments").select("*").in_("domain_id", domain_ids).order("created_at", desc=False).execute()
        result: dict[str, list[dict]] = {}
        for c in response.data or []:
            result.setdefault(c["domain_id"], []).append(c)
        return result
    except Exception:
        return {}


def load_high_score_count(min_score: int = 80) -> int:
    """Count domains with best_score_today >= min_score."""
    try:
        client = get_supabase_client()
        response = client.table("v_domains_today").select("*").gte("best_score_today", min_score).execute()
        return len(response.data) if response.data else 0
    except Exception:
        return 0
