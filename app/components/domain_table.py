from urllib.parse import urlparse

import streamlit as st


def render_domain_table(df, on_status_change=None, on_add_comment=None, comments_data: dict[str, list[dict]] | None = None):
    """Render an editable domain table with inline comment popovers.

    Works with any DataFrame. Detects columns by name:
      - 'Site' → clickable link
      - 'Score' → bold
      - 'Status' → selectbox
      - 'Comments' → popover button

    Args:
        df: pandas DataFrame with domain data.
        on_status_change: callback(domain_id, new_status).
        on_add_comment: callback(domain_id, author_name, message).
        comments_data: dict mapping domain_id -> list of comment dicts.
    """
    if df is None or df.empty:
        st.info("No domains found. Try adjusting filters or wait for the next crawl.")
        return

    display_cols = [c for c in df.columns if c not in ("id",)]

    col_weights = []
    for c in display_cols:
        if c == "Site":
            col_weights.append(2)
        elif c == "Summary":
            col_weights.append(3)
        elif c in ("Comments", "Score", "Status"):
            col_weights.append(1)
        else:
            col_weights.append(1)

    cols = st.columns(col_weights)
    for col, header in zip(cols, display_cols):
        col.markdown(f"**{header}**")

    for _, row in df.iterrows():
        domain_id = row.get("id")
        cols = st.columns(col_weights)

        for i, col_name in enumerate(display_cols):
            value = row.get(col_name, "")

            if col_name == "Site":
                display_name = urlparse(str(value)).netloc or str(value)
                cols[i].markdown(f"[{display_name}]({value})")

            elif col_name == "Score":
                cols[i].markdown(f"**{value}**")

            elif col_name == "Status":
                status = str(value) if value else "pending"
                new_status = cols[i].selectbox(
                    "Status",
                    options=["pending", "ok", "exists", "bad"],
                    index=["pending", "ok", "exists", "bad"].index(status) if status in ["pending", "ok", "exists", "bad"] else 0,
                    key=f"status_{domain_id}_{i}",
                    label_visibility="collapsed",
                )
                if new_status != status and on_status_change:
                    on_status_change(domain_id, new_status)

            elif col_name == "Comments":
                comment_count = int(value) if value else 0
                with cols[i].popover(f"💬 {comment_count}", use_container_width=True):
                    domain_comments = (comments_data or {}).get(domain_id, [])
                    for comment in domain_comments:
                        ts = comment.get("created_at", "")
                        time_str = str(ts)[:19] if ts else ""
                        st.markdown(
                            f"**{comment.get('author_name', 'Anonymous')}** "
                            f"<span style='color:gray;font-size:0.8em'>{time_str}</span>\n\n"
                            f"{comment.get('message', '')}",
                            unsafe_allow_html=True,
                        )
                        st.divider()

                    if on_add_comment:
                        author = st.text_input("Name", key=f"pop_name_{domain_id}")
                        message = st.text_input("Message", key=f"pop_msg_{domain_id}")
                        if st.button("Add", key=f"pop_add_{domain_id}"):
                            if author and message:
                                on_add_comment(domain_id, author, message)

            else:
                cols[i].write(str(value))
