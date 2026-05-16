from datetime import date

import streamlit as st

from app.data_loader import CATEGORY_FILTER_OPTIONS, SORT_OPTIONS, STATUS_FILTER_OPTIONS


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


def render_filters(show_reviewed_default: bool = False, expanded: bool = True) -> dict:
    """Render the dashboard filter controls and return selected values.

    Returns dict with keys:
        search_query, status_filter, category_filter, show_reviewed, sort_by, min_score, date_start, date_end
    """
    with st.expander("Filters", expanded=expanded):
        st.markdown('<span class="tf-filters-anchor"></span>', unsafe_allow_html=True)
        top_cols = st.columns([1.15, 1.45, 0.8], gap="medium", vertical_alignment="center")

        with top_cols[0]:
            date_range = st.date_input(
                "Date range",
                value=(date.today(), date.today()),
                key="filter_date_range",
            )

        with top_cols[1]:
            search_query = st.text_input(
                "Search",
                placeholder="Search domains",
                label_visibility="collapsed",
                key="filter_search",
            )

        with top_cols[2]:
            show_reviewed = st.toggle("Show reviewed", value=show_reviewed_default, key="filter_show_reviewed")

        bottom_cols = st.columns([1, 1, 1], gap="medium", vertical_alignment="center")

        with bottom_cols[0]:
            status_filter = st.selectbox(
                "Status",
                STATUS_FILTER_OPTIONS,
                label_visibility="collapsed",
                key="filter_status",
            )

        with bottom_cols[1]:
            category_filter = st.selectbox(
                "Category",
                CATEGORY_FILTER_OPTIONS,
                label_visibility="collapsed",
                key="filter_category",
            )

        with bottom_cols[2]:
            sort_by = st.selectbox(
                "Sort",
                SORT_OPTIONS,
                label_visibility="collapsed",
                key="filter_sort",
            )

    date_start, date_end = _normalize_date_range(date_range)

    return {
        "search_query": search_query,
        "status_filter": status_filter,
        "category_filter": category_filter,
        "show_reviewed": show_reviewed,
        "sort_by": sort_by,
        "min_score": 0,
        "date_start": date_start,
        "date_end": date_end,
    }
