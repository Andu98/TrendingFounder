from datetime import datetime

import pytz
import streamlit as st

from src.config.settings import settings


def render_comments_dialog(domain_id: str, comments: list[dict], on_add=None):
    """Render a comments modal for a domain.

    Args:
        domain_id: The domain UUID.
        comments: List of comment dicts with keys: author_name, message, created_at.
        on_add: callback(domain_id, author_name, message).
    """
    with st.expander(f"Comments ({len(comments)})", expanded=False):
        for comment in comments:
            ts = comment.get("created_at", "")
            if ts:
                try:
                    dt = datetime.fromisoformat(ts.replace("Z", "+00:00"))
                    tz = pytz.timezone(settings.app_timezone)
                    local_dt = dt.astimezone(tz)
                    time_str = local_dt.strftime("%Y-%m-%d %H:%M")
                except ValueError, AttributeError:
                    time_str = str(ts)
            else:
                time_str = ""

            st.markdown(
                f"**{comment.get('author_name', 'Anonymous')}** "
                f"<span style='color:gray;font-size:0.8em'>{time_str}</span>\n\n"
                f"{comment.get('message', '')}",
                unsafe_allow_html=True,
            )
            st.divider()

        col_name, col_msg, col_btn = st.columns([2, 4, 1])

        with col_name:
            author = st.text_input("Name", key=f"name_{domain_id}")

        with col_msg:
            message = st.text_input("Message", key=f"msg_{domain_id}")

        with col_btn:
            if st.button("Add", key=f"add_{domain_id}"):
                if author and message and on_add:
                    on_add(domain_id, author, message)
