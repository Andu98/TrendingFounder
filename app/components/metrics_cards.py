import streamlit as st


def _metric_card(label: str, value: str | int, detail: str = "") -> str:
    detail_html = f"<div class='tf-metric-detail'>{detail}</div>" if detail else ""
    return (
        "<div class='tf-metric-card'>"
        f"<div class='tf-metric-label'>{label}</div>"
        f"<div class='tf-metric-value'>{value}</div>"
        f"{detail_html}"
        "</div>"
    )


def render_metrics_cards(metrics: dict) -> None:
    """Render dashboard metric cards."""
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

    cards = [
        ("Countries Crawled", f"{metrics['countries_ran']} / {metrics['countries_total']}", "Completed today"),
        ("New Domains", metrics["new_domains"], "Fresh discoveries"),
        ("Duplicates", metrics["duplicates"], "Already known"),
        ("LLM Processed", metrics["llm_processed"], "Enriched domains"),
        ("High Score", metrics["high_score_today"], "Score at least 80"),
        ("Reviewed", metrics["reviewed_today"], "Triaged today"),
    ]

    for row_start in range(0, len(cards), 3):
        cols = st.columns(3, gap="medium")
        for col, (label, value, detail) in zip(cols, cards[row_start : row_start + 3]):
            col.markdown(_metric_card(label, value, detail), unsafe_allow_html=True)


def render_progress_bar(current: int, total: int) -> None:
    """Render a progress bar for crawl completion."""
    if total == 0:
        st.progress(0.0, text="No crawl run today")
        return

    pct = current / total
    st.progress(pct, text=f"{current} / {total} countries ({pct:.0%})")
