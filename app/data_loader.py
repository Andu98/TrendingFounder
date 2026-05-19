from datetime import date, datetime

import pandas as pd
import streamlit as st

from src.config.constants import COUNTRY_CODES
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
SORT_OPTIONS = ["Opportunity Score", "Score High → Low", "Score Low → High", "Newest", "Country Count"]
DEFAULT_PAGE_SIZE = 50
PAGE_SIZE_OPTIONS = [10, 25, 50, 100]

OPPORTUNITY_TYPE_OPTIONS = [
    "All Types",
    "local_marketplace",
    "b2b_saas",
    "consumer_app",
    "vertical_saas",
    "content_platform",
    "ecommerce_tool",
    "education_tool",
    "healthcare_tool",
    "logistics_tool",
    "other",
]

OPPORTUNITY_CATEGORY_OPTIONS = [
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

DASHBOARD_CACHE_TTL_SECONDS = 30


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


def _country_name(value) -> str:
    if value is None:
        return ""
    try:
        if pd.isna(value):
            return ""
    except (TypeError, ValueError):
        pass
    text = str(value).strip()
    return COUNTRY_CODES.get(text.upper(), text)


def _country_names(values: list) -> list[str]:
    names = []
    for value in values:
        name = _country_name(value)
        if name:
            names.append(name)
    return names


def _first_country_name(row: pd.Series) -> str:
    explicit_name = _country_name(row.get("first_country_name"))
    if explicit_name:
        return explicit_name

    names = row.get("Country Names") or []
    first_name = _first_value(names)
    if first_name:
        return first_name

    return _country_name(row.get("first_country_code"))


def _series(df: pd.DataFrame, column: str, default=None) -> pd.Series:
    if column in df.columns:
        return df[column]
    return pd.Series([default] * len(df), index=df.index)


def _numeric_series(df: pd.DataFrame, column: str, default: int = 0) -> pd.Series:
    return pd.to_numeric(_series(df, column, default), errors="coerce").fillna(default)


def _date_iso(value: date | datetime | str | None, default: date | None = None) -> str:
    if value is None:
        value = default or date.today()
    if isinstance(value, datetime):
        return value.date().isoformat()
    if isinstance(value, date):
        return value.isoformat()
    return str(value)


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
    df["Country Names"] = df["Country Codes"].apply(_country_names)
    df["Ranking types"] = _series(df, "ranking_types", []).apply(_as_list)
    df["First country"] = df.apply(_first_country_name, axis=1)
    df["First seen"] = _series(df, "first_seen_at").fillna(_series(df, "first_seen_date")).fillna("")
    df["First seen in range"] = _series(df, "first_seen_in_range").fillna("")
    df["Last seen in range"] = _series(df, "last_seen_in_range").fillna("")
    df["Times observed"] = _numeric_series(df, "times_observed").round().astype(int)
    df["Initial score"] = _numeric_series(df, "initial_score").round().astype(int)

    # Opportunity scoring fields
    df["Opportunity Score"] = _numeric_series(df, "opportunity_score", 0).round().astype(int)
    df["Trend Score"] = _numeric_series(df, "trend_score", 0).round().astype(int)
    df["Opportunity Category"] = _series(df, "opportunity_category", "").fillna("").replace("", "N/A")
    df["Opportunity Type"] = _series(df, "opportunity_type", "").fillna("").replace("", "N/A")
    df["Opportunity Confidence"] = _numeric_series(df, "opportunity_confidence", 0).round().astype(int)
    df["Opportunity Summary"] = _series(df, "opportunity_summary", "").fillna("")
    df["Opportunity Idea"] = _series(df, "opportunity_idea", "").fillna("")
    df["Opportunity Breakdown"] = _series(df, "opportunity_breakdown", None)

    columns = [
        "id",
        "Domain",
        "Site",
        "Summary",
        "Score",
        "First country",
        "Countries",
        "Country Codes",
        "Country Names",
        "Ranking types",
        "Status",
        "Comments",
        "Category",
        "Business Model",
        "Target Users",
        "Localization Angle",
        "Risk Notes",
        "First seen",
        "First seen in range",
        "Last seen in range",
        "Times observed",
        "Initial score",
        "Opportunity Score",
        "Trend Score",
        "Opportunity Category",
        "Opportunity Type",
        "Opportunity Confidence",
        "Opportunity Summary",
        "Opportunity Idea",
        "Opportunity Breakdown",
    ]
    return df[[column for column in columns if column in df.columns]]


@st.cache_data(ttl=DASHBOARD_CACHE_TTL_SECONDS, show_spinner=False)
def load_collected_data(
    show_reviewed: bool = False,
    sort_by: str = "Score High → Low",
    search_query: str = "",
    status_filter: str = "All Statuses",
    category_filter: str = "All Categories",
    date_start: date | datetime | str | None = None,
    date_end: date | datetime | str | None = None,
    page: int = 1,
    page_size: int = DEFAULT_PAGE_SIZE,
    min_opportunity_score: int = 0,
    min_opportunity_confidence: int = 0,
    opportunity_type_filter: str = "All Types",
    hide_global_giants: bool = False,
) -> tuple[pd.DataFrame, int]:
    """Load filtered domain rows through the Supabase range RPC."""
    try:
        start_iso = _date_iso(date_start)
        end_iso = _date_iso(date_end) if date_end is not None else start_iso
        page = max(1, int(page or 1))
        page_size = max(1, int(page_size or DEFAULT_PAGE_SIZE))

        client = get_supabase_client()
        response = (
            client.rpc(
                "get_domains_for_range",
                {
                    "start_date": start_iso,
                    "end_date": end_iso,
                    "show_reviewed": show_reviewed,
                    "status_filter": status_filter,
                    "category_filter": category_filter,
                    "search_query": search_query,
                    "sort_by": sort_by,
                    "page": page,
                    "page_size": page_size,
                    "min_opportunity_score": min_opportunity_score,
                    "min_opportunity_confidence": min_opportunity_confidence,
                    "opportunity_type_filter": opportunity_type_filter,
                    "hide_global_giants": hide_global_giants,
                },
            )
            .execute()
        )

        if not response.data:
            return pd.DataFrame(), 0

        df = pd.DataFrame(response.data)
        total_count = int(_numeric_series(df, "total_count").max()) if "total_count" in df.columns else len(df)
        df = _enrich_domain_details(df)
        return _format_today_dataframe(df), total_count

    except Exception as e:
        st.error(f"Failed to load data: {e}")
        return pd.DataFrame(), 0


def load_today_data(
    show_reviewed: bool = False,
    sort_by: str = "Score High → Low",
    min_score: int = 0,
    search_query: str = "",
    status_filter: str = "All Statuses",
    category_filter: str = "All Categories",
) -> pd.DataFrame:
    """Load today's domains. Kept for legacy Streamlit pages."""
    df, _ = load_collected_data(
        show_reviewed=show_reviewed,
        sort_by=sort_by,
        search_query=search_query,
        status_filter=status_filter,
        category_filter=category_filter,
        date_start=date.today(),
        date_end=date.today(),
        page=1,
        page_size=10_000,
    )
    if min_score and "Score" in df.columns:
        return df[df["Score"] >= min_score]
    return df


@st.cache_data(ttl=DASHBOARD_CACHE_TTL_SECONDS, show_spinner=False)
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


@st.cache_data(ttl=DASHBOARD_CACHE_TTL_SECONDS, show_spinner=False)
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


@st.cache_data(ttl=DASHBOARD_CACHE_TTL_SECONDS, show_spinner=False)
def load_high_score_count(min_score: int = 80) -> int:
    """Count domains with best_score_today >= min_score."""
    try:
        client = get_supabase_client()
        response = client.table("v_domains_today").select("*").gte("best_score_today", min_score).execute()
        return len(response.data) if response.data else 0
    except Exception:
        return 0


@st.cache_data(ttl=DASHBOARD_CACHE_TTL_SECONDS, show_spinner=False)
def load_reviewed_count() -> int:
    """Count today's domains that have been reviewed."""
    try:
        client = get_supabase_client()
        response = client.table("v_domains_today").select("id").neq("review_status", "pending").execute()
        return len(response.data) if response.data else 0
    except Exception:
        return 0


@st.cache_data(ttl=DASHBOARD_CACHE_TTL_SECONDS, show_spinner=False)
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


def clear_dashboard_caches() -> None:
    """Clear cached dashboard reads after a write."""
    for loader in (
        load_collected_data,
        load_stats,
        load_comments,
        load_high_score_count,
        load_reviewed_count,
        load_country_progress,
    ):
        loader.clear()
