import streamlit as st


def render_filters() -> dict:
    """Render filter controls and return selected values.

    Returns dict with keys:
        show_reviewed (bool), sort_by (str), min_score (int)
    """
    col1, col2, col3 = st.columns(3)

    with col1:
        show_reviewed = st.checkbox("Show reviewed", value=False)

    with col2:
        sort_by = st.selectbox(
            "Sort by",
            ["Score (desc)", "Score (asc)", "Newest", "Country count"],
        )

    with col3:
        min_score = st.slider("Min score", 0, 200, 0)

    return {
        "show_reviewed": show_reviewed,
        "sort_by": sort_by,
        "min_score": min_score,
    }
