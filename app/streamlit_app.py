import sys
from pathlib import Path

import streamlit as st

# Add project root to sys.path so we can import from src/
project_root = Path(__file__).resolve().parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from app.components.filters import render_filters
from app.components.metrics_cards import render_metrics_cards


def render():
    st.set_page_config(
        page_title="TrendingFounder",
        page_icon="🔍",
        layout="wide",
    )

    st.title("TrendingFounder")
    st.caption("Global Trending Sites Discovery Platform")

    st.page_link("pages/1_Today.py", label="Today")
    st.page_link("pages/2_This_Week.py", label="This Week")
    st.page_link("pages/3_Stats.py", label="Stats")

    st.divider()

    st.markdown("""
        ### Welcome

        TrendingFounder discovers trending domains globally via Cloudflare Radar,
        deduplicates them, enriches with a local LLM, and presents them in a
        dashboard for triage.

        **Getting started:**
        1. Navigate to **Today** to see the best scoring domains discovered today.
        2. Use **This Week** for a broader view of trends over the last 7 days.
        3. Check **Stats** for crawl progress and platform metrics.
        """)

    render_metrics_cards({})
    render_filters()


if __name__ == "__main__":
    render()
