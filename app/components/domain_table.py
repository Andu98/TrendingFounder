from datetime import datetime
from html import escape
from math import isnan
from urllib.parse import urlparse

import streamlit as st

from src.config.constants import COUNTRY_CODES

STATUS_OPTIONS = ["pending", "ok", "exists", "bad"]


def _is_blank(value) -> bool:
    if value is None:
        return True
    if isinstance(value, float):
        return isnan(value)
    return str(value).strip() == ""


def _text(value, default: str = "") -> str:
    if _is_blank(value):
        return default
    return str(value)


def _int(value, default: int = 0) -> int:
    if _is_blank(value):
        return default
    try:
        return int(float(value))
    except (TypeError, ValueError):
        return default


def _list(value) -> list[str]:
    if isinstance(value, list):
        return [str(item) for item in value if not _is_blank(item)]
    if isinstance(value, tuple | set):
        return [str(item) for item in value if not _is_blank(item)]
    if _is_blank(value):
        return []
    text = str(value).strip()
    if "," in text:
        return [part.strip() for part in text.split(",") if part.strip()]
    return [text]


def _country_name(value) -> str:
    text = _text(value).strip()
    return COUNTRY_CODES.get(text.upper(), text)


def _country_names(value) -> list[str]:
    return [name for item in _list(value) if (name := _country_name(item))]


def _domain_from_url(url: str, fallback: str = "") -> str:
    parsed = urlparse(url)
    return parsed.netloc or fallback or url


def _truncate(value: str, max_chars: int = 135) -> str:
    value = value.strip()
    if len(value) <= max_chars:
        return value
    return f"{value[: max_chars - 3].rstrip()}..."


def _format_timestamp(value) -> str:
    text = _text(value)
    if not text:
        return "N/A"
    try:
        dt = datetime.fromisoformat(text.replace("Z", "+00:00"))
        return dt.strftime("%Y-%m-%d %H:%M")
    except ValueError:
        return text


def _pill(label: str, class_name: str = "") -> str:
    if not label:
        return ""
    return f"<span class='tf-pill {class_name}'>{escape(label)}</span>"


def _business_model_pill(label: str) -> str:
    if label.strip().lower() in ("", "unknown", "n/a", "none"):
        return ""
    return _pill(label, "tf-model-pill")


def _pills(labels: list[str], class_name: str = "") -> str:
    pills = "".join(_pill(label, class_name) for label in labels)
    return f"<div class='tf-pill-row'>{pills}</div>" if pills else "<span class='tf-muted'>N/A</span>"


def _score_badge(score: int) -> str:
    if score >= 80:
        variant = "high"
    elif score >= 50:
        variant = "medium"
    else:
        variant = "low"
    return f"<span class='tf-score tf-score-{variant}'>{score}</span>"


def _status_index(status: str) -> int:
    return STATUS_OPTIONS.index(status) if status in STATUS_OPTIONS else 0


def _status_pill(status: str) -> str:
    status = status if status in STATUS_OPTIONS else "pending"
    return f"<span class='tf-status-pill tf-status-{status}'>{escape(status)}</span>"


def _comment_html(comment: dict) -> str:
    author = escape(_text(comment.get("author_name"), "Anonymous"))
    message = escape(_text(comment.get("message")))
    created_at = escape(_format_timestamp(comment.get("created_at")))
    return (
        "<div class='tf-comment'>"
        "<div class='tf-comment-line'></div>"
        "<div class='tf-comment-body'>"
        f"<div><strong>{author}</strong><span>{created_at}</span></div>"
        f"<p>{message}</p>"
        "</div>"
        "</div>"
    )


def _render_comments(domain_id: str, comment_count: int, comments: list[dict], on_add_comment=None) -> None:
    with st.popover(str(comment_count), use_container_width=True):
        st.markdown("<div class='tf-popover-title'>Comments</div>", unsafe_allow_html=True)

        if comments:
            for comment in comments:
                st.markdown(_comment_html(comment), unsafe_allow_html=True)
        else:
            st.caption("No comments yet.")

        st.divider()
        author = st.text_input("Name", value="You", key=f"comment_author_{domain_id}")
        message = st.text_area(
            "New comment",
            placeholder="Add a note for this domain...",
            height=90,
            key=f"comment_message_{domain_id}",
        )
        if st.button("Add comment", key=f"comment_add_{domain_id}", type="primary", use_container_width=True):
            if not message.strip():
                st.warning("Write a comment first.")
                return
            if on_add_comment:
                on_add_comment(domain_id, author.strip() or "You", message.strip())


def _detail_value(label: str, value: str) -> str:
    return (
        "<div class='tf-detail-item'>"
        f"<span>{escape(label)}</span>"
        f"<strong>{escape(value) if value else 'N/A'}</strong>"
        "</div>"
    )


def render_domain_table(
    df,
    on_status_change=None,
    on_add_comment=None,
    comments_data: dict[str, list[dict]] | None = None,
):
    """Render responsive domain cards with inline status and comments actions."""
    if df is None or df.empty:
        st.info("No domains found. Try adjusting filters or wait for the next crawl.")
        return

    st.markdown(
        """
        <div class="tf-table-head-wrapper">
            <div class="tf-table-head tf-table-head-desktop">
                <span>Domain</span>
                <span>Score</span>
                <span>Summary</span>
                <span>Country</span>
                <span>Status</span>
                <span>Actions</span>
            </div>
            <div class="tf-table-head tf-table-head-mobile">
                <span>Domain</span>
                <span>Score</span>
                <span>Review</span>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    comments_data = comments_data or {}

    for _, row in df.iterrows():
        domain_id = _text(row.get("id"))
        site_url = _text(row.get("Site"))
        domain_name = _text(row.get("Domain")) or _domain_from_url(site_url)
        summary = _truncate(_text(row.get("Summary"), "No summary yet"))
        score = _int(row.get("Score"))
        status = _text(row.get("Status"), "pending")
        category = _text(row.get("Category"), "Other")
        business_model = _text(row.get("Business Model"), "unknown")
        model_pill = _business_model_pill(business_model)
        score_badge = _score_badge(score)
        comment_count = _int(row.get("Comments"))
        countries = _int(row.get("Countries"))
        first_country = _country_name(row.get("First country")) or "N/A"
        country_names = _country_names(row.get("Country Names")) or _country_names(row.get("Country Codes"))
        if not country_names and first_country != "N/A":
            country_names = [first_country]
        ranking_types = _list(row.get("Ranking types"))

        with st.container(border=True):
            cols = st.columns([2.0, 0.65, 3.1, 0.65, 1.8, 0.6], gap="medium", vertical_alignment="center")

            cols[0].markdown(
                (
                    "<div class='tf-domain-cell'>"
                    "<div class='tf-domain-primary'>"
                    f"<a class='tf-domain-link' href='{escape(site_url)}' target='_blank'>{escape(domain_name)}</a>"
                    f"<div class='tf-score-mobile'>{score_badge}</div>"
                    "</div>"
                    "<div class='tf-domain-pills'>"
                    f"{_pill(category, 'tf-category-pill')}"
                    f"{model_pill}"
                    "</div>"
                    "</div>"
                ),
                unsafe_allow_html=True,
            )
            cols[1].markdown(score_badge, unsafe_allow_html=True)
            cols[2].markdown(
                (
                    "<div class='tf-mobile-field-label'>Summary</div>"
                    f"<div class='tf-summary' title='{escape(summary)}'>{escape(summary)}</div>"
                ),
                unsafe_allow_html=True,
            )
            extra_countries = f" +{countries - 1}" if countries > 1 else ""
            cols[3].markdown(
                (
                    "<div class='tf-mobile-field-label'>Country</div>"
                    f"<span class='tf-country'>{escape(first_country)}{escape(extra_countries)}</span>"
                ),
                unsafe_allow_html=True,
            )

            cols[4].markdown(
                "<div class='tf-mobile-field-label tf-mobile-widget-label'>Status</div>",
                unsafe_allow_html=True,
            )
            new_status = cols[4].selectbox(
                "Status",
                STATUS_OPTIONS,
                index=_status_index(status),
                key=f"status_{domain_id}",
                label_visibility="collapsed",
            )
            if new_status != status and on_status_change:
                on_status_change(domain_id, new_status)

            with cols[5]:
                st.markdown(
                    "<div class='tf-mobile-field-label tf-mobile-widget-label'>Comments</div>",
                    unsafe_allow_html=True,
                )
                _render_comments(domain_id, comment_count, comments_data.get(domain_id, []), on_add_comment)

            st.markdown("<div class='tf-details-spacer'></div>", unsafe_allow_html=True)
            with st.expander("Details", expanded=False):
                detail_cols = st.columns([1.25, 1.25, 2], gap="large")

                with detail_cols[0]:
                    st.markdown("<div class='tf-detail-title'>Countries Found In</div>", unsafe_allow_html=True)
                    st.markdown(_pills(country_names, "tf-country-pill"), unsafe_allow_html=True)

                with detail_cols[1]:
                    st.markdown("<div class='tf-detail-title'>Ranking Types</div>", unsafe_allow_html=True)
                    st.markdown(_pills(ranking_types, "tf-ranking-pill"), unsafe_allow_html=True)

                with detail_cols[2]:
                    range_details = ""
                    if not _is_blank(row.get("First seen in range")):
                        range_details += _detail_value(
                            "First seen in range",
                            _format_timestamp(row.get("First seen in range")),
                        )
                    if not _is_blank(row.get("Last seen in range")):
                        range_details += _detail_value(
                            "Last seen in range",
                            _format_timestamp(row.get("Last seen in range")),
                        )
                    times_observed = _int(row.get("Times observed"))
                    if times_observed:
                        range_details += _detail_value("Times observed", str(times_observed))

                    details_html = (
                        "<div class='tf-detail-grid'>"
                        + _detail_value("Target users", _text(row.get("Target Users"), "N/A"))
                        + _detail_value("Localization angle", _text(row.get("Localization Angle"), "N/A"))
                        + _detail_value("Risk notes", _text(row.get("Risk Notes"), "None"))
                        + _detail_value("First seen", _format_timestamp(row.get("First seen")))
                        + range_details
                        + _detail_value("Initial score", str(_int(row.get("Initial score"))))
                        + _detail_value("Review status", status)
                        + "</div>"
                    )
                    st.markdown(details_html, unsafe_allow_html=True)
