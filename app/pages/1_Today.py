import sys
from pathlib import Path

import streamlit as st

project_root = Path(__file__).resolve().parent.parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from app.components.domain_table import render_domain_table
from app.components.filters import render_filters
from app.components.metrics_cards import render_metrics_cards
from app.data_loader import load_comments, load_high_score_count, load_stats, load_today_data
from src.db.repositories import CommentRepository, DomainRepository
from src.config.constants import ReviewStatus

st.set_page_config(page_title="Today", page_icon="📅", layout="wide")

st.title("Best Score Today Across the World")

filters = render_filters()

stats = load_stats()
render_metrics_cards(
    {
        "countries_ran": stats.get("countries_completed", 0),
        "countries_total": stats.get("countries_total", 0),
        "new_domains": stats.get("new_domains_count", 0),
        "duplicates": stats.get("duplicate_domains_count", 0),
        "high_score_today": load_high_score_count(),
    }
)

st.divider()

df = load_today_data(
    show_reviewed=filters["show_reviewed"],
    sort_by=filters["sort_by"],
    min_score=filters["min_score"],
)

if not df.empty:
    comments_data = load_comments(df["id"].tolist())
else:
    comments_data = {}


def on_status_change(domain_id: str, new_status: str):
    repo = DomainRepository()
    review_status = ReviewStatus(new_status)
    repo.update_review_status(domain_id, review_status)
    st.rerun()


def on_add_comment(domain_id: str, author: str, message: str):
    repo = CommentRepository()
    repo.add_comment(domain_id, author, message)
    st.rerun()


render_domain_table(df, on_status_change=on_status_change, on_add_comment=on_add_comment, comments_data=comments_data)
