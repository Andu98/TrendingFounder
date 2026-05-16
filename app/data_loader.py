import pandas as pd
import streamlit as st

from src.db.repositories import CrawlRunRepository
from src.db.supabase_client import get_supabase_client

CATEGORY_FILTER_OPTIONS = [
    "All Categories",
    "AI",
    "SaaS",
    "Ecommerce",
    "Community",
    "Entertainment",
    "Finance",
    "Education",
    "Productivity",
    "Developer Tools",
    "Marketplace",
    "Games",
    "Social",
    "Adult",
    "Gambling",
    "Piracy",
    "Scam-risk",
    "Other",
]

STATUS_FILTER_OPTIONS = ["All Statuses", "pending", "ok", "exists", "bad"]
SORT_OPTIONS = ["Score High → Low", "Score Low → High", "Newest", "Country Count"]


def _as_list(value) -> list:
    if isinstance(value, list):
        return [item for item in value if item not in (None, "")]
    if isinstance(value, tuple | set):
        return [item for item in value if item not in (None, "")]
    if value is None:
        return []
    try:
        if pd.isna(value):
            return []
    except (TypeError, ValueError):
        pass
    text = str(value).strip()
    if not text:
        return []
    if "," in text:
        return [part.strip() for part in text.split(",") if part.strip()]
    return [text]


def _first_value(values: list, fallback: str = "") -> str:
    return str(values[0]) if values else fallback


def _series(df: pd.DataFrame, column: str, default=None) -> pd.Series:
    if column in df.columns:
        return df[column]
    return pd.Series([default] * len(df), index=df.index)


def _numeric_series(df: pd.DataFrame, column: str, default: int = 0) -> pd.Series:
    return pd.to_numeric(_series(df, column, default), errors="coerce").fillna(default)


def _display_url(row: pd.Series) -> str:
    display_url = row.get("display_url")
    if isinstance(display_url, str) and display_url.strip():
        return display_url
    domain = row.get("normalized_domain", "")
    return f"https://{domain}" if domain else ""


def _enrich_domain_details(df: pd.DataFrame) -> pd.DataFrame:
    """Attach domain-table-only fields not present in the dashboard view."""
    if df.empty or "id" not in df.columns:
        return df

    try:
        client = get_supabase_client()
        domain_ids = df["id"].dropna().astype(str).tolist()
        if not domain_ids:
            return df

        response = (
            client.table("domains")
            .select(
                "id,first_seen_at,first_country_code,first_country_name,first_ranking_type,"
                "llm_target_users,llm_localization_angle,llm_risk_notes,initial_score"
            )
            .in_("id", domain_ids)
            .execute()
        )
        if not response.data:
            return df

        details_df = pd.DataFrame(response.data)
        merged = df.merge(details_df, on="id", how="left", suffixes=("", "_detail"))

        if "initial_score_detail" in merged.columns:
            merged["initial_score"] = _series(merged, "initial_score").fillna(merged["initial_score_detail"])

        return merged
    except Exception:
        return df


def _format_today_dataframe(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return df

    df = df.copy()
    df["Site"] = df.apply(_display_url, axis=1)
    df["Domain"] = _series(df, "normalized_domain", "").fillna("")
    df["Summary"] = _series(df, "llm_summary", "No summary yet").fillna("No summary yet")
    df["Score"] = _numeric_series(df, "best_score_today").round().astype(int)
    df["Category"] = _series(df, "llm_category", "Other").fillna("Other").replace("", "Other")
    df["Business Model"] = _series(df, "llm_business_model", "unknown").fillna("unknown").replace("", "unknown")
    df["Target Users"] = _series(df, "llm_target_users", "N/A").fillna("N/A").replace("", "N/A")
    df["Localization Angle"] = _series(df, "llm_localization_angle", "N/A").fillna("N/A").replace("", "N/A")
    df["Risk Notes"] = _series(df, "llm_risk_notes", "").fillna("")
    df["Status"] = _series(df, "review_status", "pending").fillna("pending")
    df["Comments"] = _numeric_series(df, "comment_count").round().astype(int)
    df["Countries"] = _numeric_series(df, "countries_today").round().astype(int)
    df["Country Codes"] = _series(df, "country_codes", []).apply(_as_list)
    df["Ranking types"] = _series(df, "ranking_types", []).apply(_as_list)
    df["First country"] = df.apply(
        lambda row: _first_value(row["Country Codes"], str(row.get("first_country_code") or "")),
        axis=1,
    )
    df["First seen"] = _series(df, "first_seen_at").fillna(_series(df, "first_seen_date")).fillna("")
    df["Initial score"] = _numeric_series(df, "initial_score").round().astype(int)

    columns = [
        "id",
        "Domain",
        "Site",
        "Summary",
        "Score",
        "First country",
        "Countries",
        "Country Codes",
        "Ranking types",
        "Status",
        "Comments",
        "Category",
        "Business Model",
        "Target Users",
        "Localization Angle",
        "Risk Notes",
        "First seen",
        "Initial score",
    ]
    return df[[column for column in columns if column in df.columns]]


def load_today_data(
    show_reviewed: bool = False,
    sort_by: str = "Score High → Low",
    min_score: int = 0,
    search_query: str = "",
    status_filter: str = "All Statuses",
    category_filter: str = "All Categories",
) -> pd.DataFrame:
    """Load today's domains from Supabase view."""
    try:
        client = get_supabase_client()
        query = client.table("v_domains_today").select("*")

        if status_filter and status_filter != "All Statuses":
            query = query.eq("review_status", status_filter)
        elif not show_reviewed:
            query = query.eq("review_status", "pending")

        response = query.execute()

        if not response.data:
            return pd.DataFrame()

        df = pd.DataFrame(response.data)
        df = _enrich_domain_details(df)

        if "best_score_today" in df.columns:
            df = df[df["best_score_today"] >= min_score]

        if search_query:
            query_text = search_query.strip()
            if query_text:
                domain_series = _series(df, "normalized_domain", "").astype(str)
                url_series = _series(df, "display_url", "").astype(str)
                df = df[
                    domain_series.str.contains(query_text, case=False, na=False)
                    | url_series.str.contains(query_text, case=False, na=False)
                ]

        if category_filter and category_filter != "All Categories":
            df = df[_series(df, "llm_category", "Other").fillna("Other") == category_filter]

        if df.empty:
            return pd.DataFrame()

        if sort_by in ("Score High → Low", "Score (desc)"):
            df = df.sort_values("best_score_today", ascending=False)
        elif sort_by in ("Score Low → High", "Score (asc)"):
            df = df.sort_values("best_score_today", ascending=True)
        elif sort_by == "Newest":
            newest_col = "first_seen_at" if "first_seen_at" in df.columns else "first_seen_date"
            df = df.sort_values(newest_col, ascending=False)
        elif sort_by in ("Country Count", "Country count"):
            df = df.sort_values("countries_today", ascending=False)

        return _format_today_dataframe(df)

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
        if not domain_ids:
            return {}
        client = get_supabase_client()
        response = (
            client.table("domain_comments")
            .select("*")
            .in_("domain_id", domain_ids)
            .order("created_at", desc=False)
            .execute()
        )
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


def load_reviewed_count() -> int:
    """Count today's domains that have been reviewed."""
    try:
        client = get_supabase_client()
        response = client.table("v_domains_today").select("id").neq("review_status", "pending").execute()
        return len(response.data) if response.data else 0
    except Exception:
        return 0


def load_country_progress() -> pd.DataFrame:
    """Load country-level crawl progress for today's run."""
    try:
        client = get_supabase_client()
        response = client.table("v_crawl_country_progress").select("*").execute()
        if response.data:
            return pd.DataFrame(response.data)
    except Exception:
        pass
    return pd.DataFrame()
