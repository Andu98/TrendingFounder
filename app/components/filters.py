from datetime import date

import streamlit as st

from app.data_loader import CATEGORY_FILTER_OPTIONS, SORT_OPTIONS, STATUS_FILTER_OPTIONS

STATUS_CHECKBOX_OPTIONS = STATUS_FILTER_OPTIONS[1:]


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


def render_filters(show_reviewed_default: bool = False, expanded: bool = True) -> dict:
    """Render the dashboard filter controls and return selected values.

    Returns dict with keys:
        search_query, status_filter, category_filter, show_reviewed, sort_by, min_score, date_start, date_end
    """
    with st.expander("Filters", expanded=expanded):
        st.markdown('<span class="tf-filters-anchor"></span>', unsafe_allow_html=True)
        cols = st.columns([1.25, 1.1, 1, 0.86], gap="medium", vertical_alignment="bottom")

        with cols[0]:
            date_range = st.date_input(
                "Date range",
                value=(date.today(), date.today()),
                key="filter_date_range",
            )

        with cols[1]:
            category_filter = st.selectbox(
                "Category",
                CATEGORY_FILTER_OPTIONS,
                key="filter_category",
            )

        with cols[2]:
            sort_by = st.selectbox(
                "Sort",
                SORT_OPTIONS,
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
    }
