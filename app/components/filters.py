import streamlit as st

from app.data_loader import CATEGORY_FILTER_OPTIONS, SORT_OPTIONS, STATUS_FILTER_OPTIONS


def render_filters(show_reviewed_default: bool = False, expanded: bool = True) -> dict:
    """Render the dashboard filter controls and return selected values.

    Returns dict with keys:
        search_query, status_filter, category_filter, show_reviewed, sort_by, min_score
    """
    with st.expander("Filters", expanded=expanded):
        st.markdown('<span class="tf-filters-anchor"></span>', unsafe_allow_html=True)
        top_cols = st.columns([1.25, 1.25, 1.25, 1.25], gap="medium")

        with top_cols[0]:
            search_query = st.text_input(
                "Search",
                placeholder="Search domains",
                label_visibility="collapsed",
                key="filter_search",
            )

        with top_cols[1]:
            status_filter = st.selectbox(
                "Status",
                STATUS_FILTER_OPTIONS,
                label_visibility="collapsed",
                key="filter_status",
            )

        with top_cols[2]:
            category_filter = st.selectbox(
                "Category",
                CATEGORY_FILTER_OPTIONS,
                label_visibility="collapsed",
                key="filter_category",
            )

        with top_cols[3]:
            sort_by = st.selectbox(
                "Sort",
                SORT_OPTIONS,
                label_visibility="collapsed",
                key="filter_sort",
            )

        bottom_cols = st.columns([3, 1], gap="large", vertical_alignment="center")

        with bottom_cols[0]:
            min_score = st.slider("Min Score", 0, 200, 0, key="filter_min_score")

        with bottom_cols[1]:
            show_reviewed = st.toggle("Show reviewed", value=show_reviewed_default, key="filter_show_reviewed")

    return {
        "search_query": search_query,
        "status_filter": status_filter,
        "category_filter": category_filter,
        "show_reviewed": show_reviewed,
        "sort_by": sort_by,
        "min_score": min_score,
    }
