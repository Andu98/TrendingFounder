import streamlit as st


def render_metrics_cards(metrics: dict) -> None:
    """Render a row of metric cards.

    Expected keys:
        countries_ran, countries_total, new_domains, duplicates,
        llm_processed, high_score_today, reviewed_today
    """
    cols = st.columns(4)

    defaults = {
        "countries_ran": 0,
        "countries_total": 0,
        "new_domains": 0,
        "duplicates": 0,
        "llm_processed": 0,
        "high_score_today": 0,
        "reviewed_today": 0,
    }
    metrics = {**defaults, **metrics}

    with cols[0]:
        st.metric(
            "Countries Crawled",
            f"{metrics['countries_ran']} / {metrics['countries_total']}",
        )
    with cols[1]:
        st.metric("New Domains", metrics["new_domains"])
    with cols[2]:
        st.metric("Duplicates", metrics["duplicates"])
    with cols[3]:
        st.metric("High Score (>80)", metrics["high_score_today"])


def render_progress_bar(current: int, total: int) -> None:
    """Render a progress bar for crawl completion."""
    if total == 0:
        st.progress(0.0, text="No crawl run today")
        return

    pct = current / total
    st.progress(pct, text=f"{current} / {total} countries ({pct:.0%})")
