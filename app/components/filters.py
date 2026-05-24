from datetime import date

import streamlit as st

from app.data_loader import (
    CATEGORY_FILTER_OPTIONS,
    OPPORTUNITY_TYPE_OPTIONS,
    SORT_OPTIONS,
    STATUS_FILTER_OPTIONS,
)

STATUS_CHECKBOX_OPTIONS = STATUS_FILTER_OPTIONS[1:]
CATEGORY_MULTISELECT_OPTIONS = CATEGORY_FILTER_OPTIONS
CATEGORY_MATCH_OPTIONS = CATEGORY_FILTER_OPTIONS[1:]
DEFAULT_CATEGORY_FILTER_SELECTION = ["SaaS", "Productivity", "Developer Tools"]
DEFAULT_SORT_OPTION = "Score High → Low"
DEFAULT_HIDE_GLOBAL_GIANTS = True


def _default_date_range() -> tuple[date, date]:
    today = date.today()
    if today.month == 1:
        previous_month_start = date(today.year - 1, 12, 1)
    else:
        previous_month_start = date(today.year, today.month - 1, 1)

    if today.month == 12:
        next_month = date(today.year + 1, 1, 1)
    else:
        next_month = date(today.year, today.month + 1, 1)
    month_end = date.fromordinal(next_month.toordinal() - 1)
    return previous_month_start, month_end


def _normalize_date_range(value) -> tuple[date, date]:
    today = date.today()
    if isinstance(value, date):
        return value, value
    if isinstance(value, tuple | list):
        if not value:
            return today, today
        start = value[0] or today
        end = value[1] if len(value) > 1 and value[1] else start
        return (end, start) if start > end else (start, end)
    return today, today


def _status_filter_from_values(values: dict[str, bool]) -> str:
    selected = [status for status in STATUS_CHECKBOX_OPTIONS if values.get(status)]
    if not selected:
        return "__none__"
    if len(selected) == len(STATUS_CHECKBOX_OPTIONS):
        return "All Statuses"
    return ",".join(selected)


def _coerce_category_values(value) -> list[str]:
    if isinstance(value, str):
        return [part.strip() for part in value.split(",") if part.strip()]
    if isinstance(value, tuple | list | set):
        return [str(item).strip() for item in value if item is not None and str(item).strip()]
    if value is None:
        return []
    text = str(value).strip()
    return [text] if text else []


def _category_filter_from_values(values) -> str:
    selected_values = set(_coerce_category_values(values))
    if "All Categories" in selected_values:
        return "All Categories"

    selected = [category for category in CATEGORY_MATCH_OPTIONS if category in selected_values]
    if not selected or len(selected) == len(CATEGORY_MATCH_OPTIONS):
        return "All Categories"
    return ",".join(selected)


def render_filters(show_reviewed_default: bool = False, expanded: bool = True) -> dict:
    # Alias for backward compatibility
    """Render the dashboard filter controls and return selected values.

    Returns dict with keys:
        search_query, status_filter, category_filter, show_reviewed, sort_by, min_score, date_start, date_end,
        min_opportunity_score, min_opportunity_confidence, hide_global_giants, opportunity_type_filter
    """
    with st.expander("Filters", expanded=expanded):
        st.markdown('<span class="tf-filters-anchor"></span>', unsafe_allow_html=True)
        cols = st.columns([1.2, 1.7, 1, 0.86], gap="medium", vertical_alignment="bottom")

        with cols[0]:
            date_range = st.date_input(
                "Date range",
                value=_default_date_range(),
                key="filter_date_range",
            )

        with cols[1]:
            category_values = st.multiselect(
                "Categories",
                CATEGORY_MULTISELECT_OPTIONS,
                default=DEFAULT_CATEGORY_FILTER_SELECTION,
                key="filter_categories",
            )
            category_filter = _category_filter_from_values(category_values)

        with cols[2]:
            sort_by = st.selectbox(
                "Sort",
                SORT_OPTIONS,
                index=SORT_OPTIONS.index(DEFAULT_SORT_OPTION),
                key="filter_sort",
            )

        with cols[3]:
            show_reviewed = st.toggle("Show reviewed", value=show_reviewed_default, key="filter_show_reviewed")

        st.markdown("<div class='tf-status-filter-label'>Status</div>", unsafe_allow_html=True)
        status_cols = st.columns(4, gap="small", vertical_alignment="center")
        status_values = {}
        for index, status in enumerate(STATUS_CHECKBOX_OPTIONS):
            with status_cols[index]:
                status_values[status] = st.checkbox(
                    status,
                    value=True,
                    key=f"filter_status_{status}",
                )

        st.markdown("<div class='tf-status-filter-label'>Opportunity Filters</div>", unsafe_allow_html=True)
        opp_cols = st.columns(4, gap="small", vertical_alignment="bottom")

        with opp_cols[0]:
            min_opportunity_score = st.number_input(
                "Min opportunity score",
                min_value=0,
                max_value=100,
                value=0,
                key="filter_min_opp_score",
            )

        with opp_cols[1]:
            min_opportunity_confidence = st.number_input(
                "Min confidence",
                min_value=0,
                max_value=100,
                value=0,
                key="filter_min_opp_confidence",
            )

        with opp_cols[2]:
            opportunity_type_filter = st.selectbox(
                "Opportunity type",
                OPPORTUNITY_TYPE_OPTIONS,
                key="filter_opp_type",
            )

        with opp_cols[3]:
            hide_global_giants = st.checkbox(
                "Hide global giants",
                value=DEFAULT_HIDE_GLOBAL_GIANTS,
                key="filter_hide_giants",
            )

    date_start, date_end = _normalize_date_range(date_range)
    status_filter = _status_filter_from_values(status_values)

    return {
        "search_query": "",
        "status_filter": status_filter,
        "category_filter": category_filter,
        "show_reviewed": show_reviewed,
        "sort_by": sort_by,
        "min_score": 0,
        "date_start": date_start,
        "date_end": date_end,
        "min_opportunity_score": min_opportunity_score,
        "min_opportunity_confidence": min_opportunity_confidence,
        "hide_global_giants": hide_global_giants,
        "opportunity_type_filter": opportunity_type_filter,
    }

# Alias for backward compatibility
render_filter = render_filters
