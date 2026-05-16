# ruff: noqa: E402

import sys
from html import escape
from math import isnan
from pathlib import Path

import streamlit as st
import streamlit.components.v1 as components

# Add project root to sys.path so we can import from src/
project_root = Path(__file__).resolve().parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from app.components.domain_table import render_domain_table
from app.components.filters import render_filters
from app.components.metrics_cards import render_metrics_cards, render_progress_bar
from app.data_loader import (
    CATEGORY_FILTER_OPTIONS,
    SORT_OPTIONS,
    STATUS_FILTER_OPTIONS,
    load_comments,
    load_country_progress,
    load_high_score_count,
    load_reviewed_count,
    load_stats,
    load_today_data,
)
from src.config.constants import ReviewStatus
from src.db.repositories import CommentRepository, DomainRepository

NAV_ITEMS = ["Collected Data", "Reports"]
THEME_QUERY_PARAM = "theme"
THEME_STORAGE_KEY = "tf_theme"

THEMES = {
    "Dark": {
        "bg": "#071114",
        "bg_soft": "#0b171b",
        "surface": "#0f1d22",
        "surface_2": "#13252b",
        "input_bg": "#0a171b",
        "table_head": "rgba(15, 29, 34, 0.72)",
        "border": "#21363e",
        "border_soft": "#193038",
        "card_border": "#2f4a53",
        "text": "#e7f2f4",
        "muted": "#8fa3aa",
        "placeholder": "#6f858d",
        "accent": "#18c4c7",
        "accent_2": "#3fe6c7",
        "green": "#43d990",
        "amber": "#d6a33d",
        "red": "#ef6363",
        "purple": "#a98dff",
        "blue": "#62a7ff",
        "brand_mark_text": "#062023",
        "button_active_text": "#052124",
        "toggle_track": "#20333b",
        "toggle_knob": "#e8fbfb",
        "pill_bg": "#1a2b31",
        "pill_border": "#27424b",
        "pill_text": "#c9d8dc",
        "category_bg": "rgba(24, 196, 199, 0.12)",
        "category_border": "rgba(24, 196, 199, 0.28)",
        "category_text": "#9cf5ea",
        "model_bg": "rgba(214, 163, 61, 0.13)",
        "model_border": "rgba(214, 163, 61, 0.24)",
        "model_text": "#efd188",
        "ranking_bg": "rgba(169, 141, 255, 0.12)",
        "ranking_border": "rgba(169, 141, 255, 0.25)",
        "ranking_text": "#c9baff",
        "country_pill_bg": "rgba(98, 167, 255, 0.1)",
        "country_pill_border": "rgba(98, 167, 255, 0.22)",
        "country_pill_text": "#b7d4ff",
        "score_high_bg": "rgba(67, 217, 144, 0.13)",
        "score_high_border": "rgba(67, 217, 144, 0.42)",
        "score_high_text": "#8df1bd",
        "score_medium_bg": "rgba(24, 196, 199, 0.12)",
        "score_medium_border": "rgba(24, 196, 199, 0.35)",
        "score_medium_text": "#8af7e4",
        "score_low_bg": "rgba(143, 163, 170, 0.12)",
        "score_low_border": "rgba(143, 163, 170, 0.28)",
        "score_low_text": "#c1cdd1",
        "status_pending_bg": "rgba(214, 163, 61, 0.13)",
        "status_pending_border": "rgba(214, 163, 61, 0.3)",
        "status_pending_text": "#e8cb81",
        "status_ok_bg": "rgba(67, 217, 144, 0.13)",
        "status_ok_border": "rgba(67, 217, 144, 0.34)",
        "status_ok_text": "#8df1bd",
        "status_exists_bg": "rgba(169, 141, 255, 0.13)",
        "status_exists_border": "rgba(169, 141, 255, 0.32)",
        "status_exists_text": "#c9baff",
        "status_bad_bg": "rgba(239, 99, 99, 0.13)",
        "status_bad_border": "rgba(239, 99, 99, 0.34)",
        "status_bad_text": "#ffb0b0",
        "summary": "#b7c9ce",
        "country": "#d4e4e8",
        "detail_strong": "#d7e7eb",
        "comment_text": "#cfe0e4",
        "shadow": "0 12px 36px rgba(0, 0, 0, 0.18)",
        "shadow_strong": "0 16px 44px rgba(0, 0, 0, 0.22)",
    },
    "Light": {
        "bg": "#f5f9fb",
        "bg_soft": "#edf5f7",
        "surface": "#ffffff",
        "surface_2": "#f1f7f9",
        "input_bg": "#ffffff",
        "table_head": "rgba(255, 255, 255, 0.86)",
        "border": "#d5e3e8",
        "border_soft": "#c9dce2",
        "card_border": "#b6d3dc",
        "text": "#17252b",
        "muted": "#667982",
        "placeholder": "#6f858d",
        "accent": "#11b9bd",
        "accent_2": "#078f99",
        "green": "#148b58",
        "amber": "#a76f12",
        "red": "#c84646",
        "purple": "#7561d8",
        "blue": "#2f78d8",
        "brand_mark_text": "#062023",
        "button_active_text": "#ffffff",
        "toggle_track": "#e3ebef",
        "toggle_knob": "#ffffff",
        "pill_bg": "#f2f7f8",
        "pill_border": "#d4e3e8",
        "pill_text": "#405159",
        "category_bg": "#e3fbfb",
        "category_border": "#9de4e5",
        "category_text": "#047b83",
        "model_bg": "#fff6df",
        "model_border": "#eed690",
        "model_text": "#75550b",
        "ranking_bg": "#f0edff",
        "ranking_border": "#c6baff",
        "ranking_text": "#5144a5",
        "country_pill_bg": "#e8f2ff",
        "country_pill_border": "#b8d5ff",
        "country_pill_text": "#245fae",
        "score_high_bg": "#e8fff4",
        "score_high_border": "#90e6b8",
        "score_high_text": "#11784c",
        "score_medium_bg": "#e4fbfc",
        "score_medium_border": "#94e2e4",
        "score_medium_text": "#047b83",
        "score_low_bg": "#eef4f6",
        "score_low_border": "#c7d9df",
        "score_low_text": "#53666f",
        "status_pending_bg": "#fff6df",
        "status_pending_border": "#eed690",
        "status_pending_text": "#75550b",
        "status_ok_bg": "#e8fff4",
        "status_ok_border": "#90e6b8",
        "status_ok_text": "#11784c",
        "status_exists_bg": "#f0edff",
        "status_exists_border": "#c6baff",
        "status_exists_text": "#5144a5",
        "status_bad_bg": "#fff0f0",
        "status_bad_border": "#f2b1b1",
        "status_bad_text": "#9c2e2e",
        "summary": "#43555e",
        "country": "#17252b",
        "detail_strong": "#253840",
        "comment_text": "#43555e",
        "shadow": "0 12px 32px rgba(26, 62, 72, 0.1)",
        "shadow_strong": "0 16px 40px rgba(26, 62, 72, 0.12)",
    },
}


def _theme_vars(theme_name: str) -> str:
    theme = THEMES.get(theme_name, THEMES["Dark"])
    return "\n".join(
        [f"--tf-{name.replace('_', '-')}: {value};" for name, value in theme.items()]
    )


def _theme_from_query_params() -> str | None:
    value = st.query_params.get(THEME_QUERY_PARAM)
    if isinstance(value, list):
        value = value[-1] if value else None
    if not value:
        return None

    normalized = str(value).strip().lower()
    if normalized == "dark":
        return "Dark"
    if normalized == "light":
        return "Light"
    return None


def inject_styles(theme_name: str) -> None:
    st.markdown(
        """
        <style>
        :root {
            __THEME_VARS__
        }

        .stApp {
            background: var(--tf-bg) !important;
            color: var(--tf-text);
            border-radius: 0 !important;
        }

        .stApp > div,
        .stApp > div > div,
        .stApp > div > div > div {
            border-radius: 0 !important;
        }

        .block-container {
            max-width: 100%;
            padding: 0;
            border-radius: 0 !important;
        }
        [data-testid="stSidebar"], [data-testid="collapsedControl"],
        button[data-testid="stExpandSidebarButton"],
        button[data-testid="stBaseButton-headerNoPadding"],
        button[data-testid="stBaseButton-header"],
        button[data-testid="stMainMenuButton"] {
            display: none !important;
        }

        [data-testid="stHeader"] {
            display: none !important;
        }

        .block-container {
            max-width: 100%;
            padding: 0;
            border-radius: 0 !important;
        }

        html, body, #root, .stApp {
            border-radius: 0 !important;
            overflow-x: hidden;
            overflow-y: auto !important;
        }

        .stApp > div:first-child,
        .block-container {
            border-radius: 0 !important;
        }

        /* Remove border-radius and overflow from all parents of navbar */
        .stApp > div,
        .stApp > div > div,
        .stApp > div > div > div,
        .stApp > div > div > div > div,
        .block-container > div,
        .block-container > div > div {
            border-radius: 0 !important;
            overflow: visible !important;
        }

        div[data-testid="stVerticalBlock"]:has(.tf-navbar-anchor) {
            background: var(--tf-surface);
            border-bottom: 1px solid var(--tf-border);
            padding: 0.5rem 2rem;
            width: 100vw;
            margin-left: calc(-50vw + 50%);
            margin-top: -1rem;
            position: sticky;
            top: 0;
            z-index: 100;
            border-radius: 0 !important;
        }

        /* Remove border-radius and overflow from all parents of navbar */
        .stApp > div,
        .stApp > div > div,
        .stApp > div > div > div,
        .stApp > div > div > div > div,
        .block-container > div,
        .block-container > div > div {
            border-radius: 0 !important;
            overflow: visible !important;
        }

        div[data-testid="stVerticalBlock"]:has(.tf-navbar-anchor) {
            background: var(--tf-surface);
            border-bottom: 1px solid var(--tf-border);
            padding: 0.5rem 2rem;
            width: 100vw;
            margin-left: calc(-50vw + 50%);
            margin-top: -1rem;
            position: sticky;
            top: 0;
            z-index: 100;
            border-radius: 0 !important;
        }

        /* Remove border-radius and overflow from all parents of navbar */
        .stApp > div,
        .stApp > div > div,
        .stApp > div > div > div,
        .stApp > div > div > div > div,
        .block-container > div,
        .block-container > div > div {
            border-radius: 0 !important;
            overflow: visible !important;
        }

        div[data-testid="stVerticalBlock"]:has(.tf-navbar-anchor) {
            background: var(--tf-surface);
            border-bottom: 1px solid var(--tf-border);
            padding: 0.5rem 2rem;
            width: 100vw;
            margin-left: calc(-50vw + 50%);
            margin-top: -1rem;
            position: sticky;
            top: 0;
            z-index: 100;
            border-radius: 0 !important;
        }

        /* Remove border-radius and overflow from all parents of navbar */
        .stApp > div,
        .stApp > div > div,
        .stApp > div > div > div,
        .stApp > div > div > div > div,
        .block-container > div,
        .block-container > div > div {
            border-radius: 0 !important;
            overflow: visible !important;
        }

        div[data-testid="stVerticalBlock"]:has(.tf-navbar-anchor) {
            background: var(--tf-surface);
            border-bottom: 1px solid var(--tf-border);
            padding: 0.5rem 2rem;
            width: 100vw;
            margin-left: calc(-50vw + 50%);
            margin-top: -1rem;
            position: sticky;
            top: 0;
            z-index: 100;
            border-radius: 0 !important;
        }

        /* Remove border-radius and overflow from all parents of navbar */
        .stApp > div,
        .stApp > div > div,
        .stApp > div > div > div,
        .stApp > div > div > div > div,
        .block-container > div,
        .block-container > div > div {
            border-radius: 0 !important;
            overflow: visible !important;
        }

        div[data-testid="stVerticalBlock"]:has(.tf-navbar-anchor) {
            background: var(--tf-surface);
            border-bottom: 1px solid var(--tf-border);
            padding: 0.5rem 2rem;
            width: 100vw;
            margin-left: calc(-50vw + 50%);
            margin-top: -1rem;
            position: sticky;
            top: 0;
            z-index: 100;
            border-radius: 0 !important;
        }

        /* Remove border-radius and overflow from all parents of navbar */
        .stApp > div,
        .stApp > div > div,
        .stApp > div > div > div,
        .stApp > div > div > div > div,
        .block-container > div,
        .block-container > div > div {
            border-radius: 0 !important;
            overflow: visible !important;
        }

        div[data-testid="stVerticalBlock"]:has(.tf-navbar-anchor) {
            background: var(--tf-surface);
            border-bottom: 1px solid var(--tf-border);
            padding: 0.5rem 2rem;
            width: 100vw;
            margin-left: calc(-50vw + 50%);
            margin-top: -1rem;
            position: sticky;
            top: 0;
            z-index: 100;
            border-radius: 0 !important;
        }

        /* Remove border-radius and overflow from all parents of navbar */
        .stApp > div,
        .stApp > div > div,
        .stApp > div > div > div,
        .stApp > div > div > div > div,
        .block-container > div,
        .block-container > div > div {
            border-radius: 0 !important;
            overflow: visible !important;
        }

        div[data-testid="stVerticalBlock"]:has(.tf-navbar-anchor) {
            background: var(--tf-surface);
            border-bottom: 1px solid var(--tf-border);
            padding: 0.5rem 2rem;
            width: 100vw;
            margin-left: calc(-50vw + 50%);
            margin-top: -1rem;
            position: sticky;
            top: 0;
            z-index: 100;
            border-radius: 0 !important;
        }

        /* Remove border-radius and overflow from all parents of navbar */
        .stApp > div,
        .stApp > div > div,
        .stApp > div > div > div,
        .stApp > div > div > div > div,
        .block-container > div,
        .block-container > div > div {
            border-radius: 0 !important;
            overflow: visible !important;
        }

        div[data-testid="stVerticalBlock"]:has(.tf-navbar-anchor) {
            background: var(--tf-surface);
            border-bottom: 1px solid var(--tf-border);
            padding: 0.5rem 2rem;
            width: 100vw;
            margin-left: calc(-50vw + 50%);
            margin-top: -1rem;
            position: sticky;
            top: 0;
            z-index: 100;
            border-radius: 0 !important;
        }

        /* Remove border-radius and overflow from all parents of navbar */
        .stApp > div,
        .stApp > div > div,
        .stApp > div > div > div,
        .stApp > div > div > div > div,
        .block-container > div,
        .block-container > div > div {
            border-radius: 0 !important;
            overflow: visible !important;
        }

        div[data-testid="stVerticalBlock"]:has(.tf-navbar-anchor) {
            background: var(--tf-surface);
            border-bottom: 1px solid var(--tf-border);
            padding: 0.5rem 2rem;
            width: 100vw;
            margin-left: calc(-50vw + 50%);
            margin-top: -1rem;
            position: sticky;
            top: 0;
            z-index: 100;
            border-radius: 0 !important;
        }

        /* Remove border-radius and overflow from all parents of navbar */
        .stApp > div,
        .stApp > div > div,
        .stApp > div > div > div,
        .stApp > div > div > div > div,
        .block-container > div,
        .block-container > div > div {
            border-radius: 0 !important;
            overflow: visible !important;
        }

        div[data-testid="stVerticalBlock"]:has(.tf-navbar-anchor) {
            background: var(--tf-surface);
            border-bottom: 1px solid var(--tf-border);
            padding: 0.5rem 2rem;
            width: 100vw;
            margin-left: calc(-50vw + 50%);
            margin-top: -1rem;
            position: sticky;
            top: 0;
            z-index: 100;
            border-radius: 0 !important;
        }

        /* Remove border-radius and overflow from all parents of navbar */
        .stApp > div,
        .stApp > div > div,
        .stApp > div > div > div,
        .stApp > div > div > div > div,
        .block-container > div,
        .block-container > div > div {
            border-radius: 0 !important;
            overflow: visible !important;
        }

        div[data-testid="stVerticalBlock"]:has(.tf-navbar-anchor) {
            background: var(--tf-surface);
            border-bottom: 1px solid var(--tf-border);
            padding: 0.5rem 2rem;
            width: 100vw;
            margin-left: calc(-50vw + 50%);
            margin-top: -1rem;
            position: sticky;
            top: 0;
            z-index: 100;
            border-radius: 0 !important;
        }

        /* Remove border-radius and overflow from all parents of navbar */
        .stApp > div,
        .stApp > div > div,
        .stApp > div > div > div,
        .stApp > div > div > div > div,
        .block-container > div,
        .block-container > div > div {
            border-radius: 0 !important;
            overflow: visible !important;
        }

        div[data-testid="stVerticalBlock"]:has(.tf-navbar-anchor) {
            background: var(--tf-surface);
            border-bottom: 1px solid var(--tf-border);
            padding: 0.5rem 2rem;
            width: 100vw;
            margin-left: calc(-50vw + 50%);
            margin-top: -1rem;
            position: sticky;
            top: 0;
            z-index: 100;
            border-radius: 0 !important;
        }

        /* Remove border-radius and overflow from all parents of navbar */
        .stApp > div,
        .stApp > div > div,
        .stApp > div > div > div,
        .stApp > div > div > div > div,
        .block-container > div,
        .block-container > div > div {
            border-radius: 0 !important;
            overflow: visible !important;
        }

        div[data-testid="stVerticalBlock"]:has(.tf-navbar-anchor) {
            background: var(--tf-surface);
            border-bottom: 1px solid var(--tf-border);
            padding: 0.5rem 2rem;
            width: 100vw;
            margin-left: calc(-50vw + 50%);
            margin-top: -1rem;
            position: sticky;
            top: 0;
            z-index: 100;
            border-radius: 0 !important;
        }

        /* Remove border-radius and overflow from all parents of navbar */
        .stApp > div,
        .stApp > div > div,
        .stApp > div > div > div,
        .stApp > div > div > div > div,
        .block-container > div,
        .block-container > div > div {
            border-radius: 0 !important;
            overflow: visible !important;
        }

        div[data-testid="stVerticalBlock"]:has(.tf-navbar-anchor) {
            background: var(--tf-surface);
            border-bottom: 1px solid var(--tf-border);
            padding: 0.5rem 2rem;
            width: 100vw;
            margin-left: calc(-50vw + 50%);
            margin-top: -1rem;
            position: sticky;
            top: 0;
            z-index: 100;
            border-radius: 0 !important;
        }

        /* Remove border-radius and overflow from all parents of navbar */
        .stApp > div,
        .stApp > div > div,
        .stApp > div > div > div,
        .stApp > div > div > div > div,
        .block-container > div,
        .block-container > div > div {
            border-radius: 0 !important;
            overflow: visible !important;
        }

        div[data-testid="stVerticalBlock"]:has(.tf-navbar-anchor) {
            background: var(--tf-surface);
            border-bottom: 1px solid var(--tf-border);
            padding: 0.5rem 2rem;
            width: 100vw;
            margin-left: calc(-50vw + 50%);
            margin-top: -1rem;
            position: sticky;
            top: 0;
            z-index: 100;
            border-radius: 0 !important;
        }

        /* Remove border-radius and overflow from all parents of navbar */
        .stApp > div,
        .stApp > div > div,
        .stApp > div > div > div,
        .stApp > div > div > div > div,
        .block-container > div,
        .block-container > div > div {
            border-radius: 0 !important;
            overflow: visible !important;
        }

        div[data-testid="stVerticalBlock"]:has(.tf-navbar-anchor) {
            background: var(--tf-surface);
            border-bottom: 1px solid var(--tf-border);
            padding: 0.5rem 2rem;
            width: 100vw;
            margin-left: calc(-50vw + 50%);
            margin-top: -1rem;
            position: sticky;
            top: 0;
            z-index: 100;
            border-radius: 0 !important;
        }

        /* Remove border-radius and overflow from all parents of navbar */
        .stApp > div,
        .stApp > div > div,
        .stApp > div > div > div,
        .stApp > div > div > div > div,
        .block-container > div,
        .block-container > div > div {
            border-radius: 0 !important;
            overflow: visible !important;
        }

        div[data-testid="stVerticalBlock"]:has(.tf-navbar-anchor) {
            background: var(--tf-surface);
            border-bottom: 1px solid var(--tf-border);
            padding: 0.5rem 2rem;
            width: 100vw;
            margin-left: calc(-50vw + 50%);
            margin-top: -1rem;
            position: sticky;
            top: 0;
            z-index: 100;
            border-radius: 0 !important;
        }

        /* Remove border-radius and overflow from all parents of navbar */
        .stApp > div,
        .stApp > div > div,
        .stApp > div > div > div,
        .stApp > div > div > div > div,
        .block-container > div,
        .block-container > div > div {
            border-radius: 0 !important;
            overflow: visible !important;
        }

        div[data-testid="stVerticalBlock"]:has(.tf-navbar-anchor) {
            background: var(--tf-surface);
            border-bottom: 1px solid var(--tf-border);
            padding: 0.5rem 2rem;
            width: 100vw;
            margin-left: calc(-50vw + 50%);
            margin-top: -1rem;
            position: sticky;
            top: 0;
            z-index: 100;
            border-radius: 0 !important;
        }

        /* Remove border-radius and overflow from all parents of navbar */
        .stApp > div,
        .stApp > div > div,
        .stApp > div > div > div,
        .stApp > div > div > div > div,
        .block-container > div,
        .block-container > div > div {
            border-radius: 0 !important;
            overflow: visible !important;
        }

        div[data-testid="stVerticalBlock"]:has(.tf-navbar-anchor) {
            background: var(--tf-surface);
            border-bottom: 1px solid var(--tf-border);
            padding: 0.5rem 2rem;
            width: 100vw;
            margin-left: calc(-50vw + 50%);
            margin-top: -1rem;
            position: sticky;
            top: 0;
            z-index: 100;
            border-radius: 0 !important;
        }

        div[data-testid="stVerticalBlock"]:has(.tf-navbar-anchor) > div {
            border-radius: 0 !important;
            background: transparent !important;
        }

        div[data-testid="stVerticalBlock"]:has(.tf-navbar-anchor) [data-testid="column"] {
            border-radius: 0 !important;
            background: transparent !important;
            padding: 0 !important;
        }

        div[data-testid="stVerticalBlock"]:has(.tf-navbar-anchor) [data-testid="stHorizontalBlock"] {
            border-radius: 0 !important;
            background: transparent !important;
        }

        div[data-testid="stVerticalBlock"]:has(.tf-navbar-anchor) .st-key-main_nav {
            display: flex;
            justify-content: center;
        }

        div[data-testid="stVerticalBlock"]:has(.tf-navbar-anchor) .st-key-theme_switch {
            display: flex;
            justify-content: flex-end;
        }

        .tf-content-wrapper,
        div[data-testid="stVerticalBlock"].st-key-page_content {
            box-sizing: border-box;
            max-width: 1360px;
            margin: 0 auto;
            padding: 2.25rem clamp(3rem, 4vw, 3.75rem) 3rem;
            width: 100%;
        }

        h1, h2, h3, p, span, label {
            color: var(--tf-text);
        }

        .tf-brand-title {
            color: var(--tf-text);
            font-size: 1.25rem;
            font-weight: 800;
            line-height: 1.1;
        }

        .tf-brand-subtitle,
        .tf-page-subtitle {
            color: var(--tf-muted);
            font-size: 0.82rem;
        }

        .tf-page-header {
            margin: 0.2rem 0 1.25rem;
        }

        .tf-page-title {
            color: var(--tf-text);
            font-size: 2rem;
            font-weight: 850;
            letter-spacing: 0;
            line-height: 1.08;
            margin: 0 0 0.35rem;
        }

        .st-key-main_nav div[data-testid="stPills"] {
            justify-content: center;
        }

        .st-key-main_nav button {
            background: var(--tf-surface) !important;
            border-radius: 999px !important;
            border: 1px solid var(--tf-border) !important;
            color: var(--tf-muted) !important;
            font-weight: 750 !important;
            min-height: 2.25rem;
        }

        .st-key-main_nav button[data-testid="stBaseButton-pillsActive"] {
            background: var(--tf-accent) !important;
            border-color: var(--tf-accent) !important;
            color: var(--tf-button-active-text) !important;
        }

        .st-key-theme_switch {
            display: flex;
            justify-content: flex-end;
        }

        .st-key-theme_switch label {
            color: var(--tf-muted) !important;
            font-size: 0.86rem !important;
            font-weight: 750 !important;
            gap: 0.45rem;
            white-space: nowrap;
        }

        .st-key-theme_switch label > div:first-child,
        .st-key-filter_show_reviewed label > div:first-child {
            background: var(--tf-toggle-track) !important;
            border: 1px solid var(--tf-card-border) !important;
        }

        .st-key-theme_switch label > div:first-child div,
        .st-key-filter_show_reviewed label > div:first-child div {
            background: var(--tf-toggle-knob) !important;
        }

        .st-key-theme_switch p,
        .st-key-filter_show_reviewed p {
            color: var(--tf-text) !important;
            font-weight: 750 !important;
        }

        div[data-testid="stExpander"] {
            background: var(--tf-surface);
            border: 1px solid var(--tf-card-border);
            border-radius: 14px;
            box-shadow: var(--tf-shadow-strong);
            overflow: hidden;
        }

        div[data-testid="stExpander"] summary {
            background: var(--tf-surface-2) !important;
            border-bottom: 1px solid var(--tf-card-border);
            color: var(--tf-text);
            font-weight: 750;
        }

        div[data-testid="stExpander"]:has(.tf-filters-anchor) {
            background: var(--tf-surface) !important;
            border: 1px solid var(--tf-card-border) !important;
            box-shadow: var(--tf-shadow) !important;
        }

        div[data-testid="stExpander"]:has(.tf-filters-anchor) summary {
            background: var(--tf-surface) !important;
            border-bottom: 1px solid var(--tf-card-border) !important;
        }

        [data-testid="stTextInput"] {
            min-height: 48px;
        }

        [data-testid="stTextInput"] input,
        [data-testid="stTextArea"] textarea,
        [data-baseweb="select"] > div {
            background: var(--tf-input-bg) !important;
            border: 1px solid var(--tf-border) !important;
            color: var(--tf-text) !important;
            outline: none !important;
            box-shadow: none !important;
        }

        [data-testid="stTextInput"] input,
        [data-testid="stTextArea"] textarea {
            -webkit-text-fill-color: var(--tf-text) !important;
            caret-color: var(--tf-accent) !important;
        }

        [data-testid="stTextInput"] input::placeholder,
        [data-testid="stTextArea"] textarea::placeholder {
            color: var(--tf-placeholder) !important;
            opacity: 1 !important;
            -webkit-text-fill-color: var(--tf-placeholder) !important;
        }

        [data-baseweb="select"] span,
        [data-baseweb="select"] svg {
            color: var(--tf-text) !important;
        }

        [data-testid="stTextInput"] input,
        [data-testid="stTextArea"] textarea,
        [data-baseweb="select"] * {
            font-size: 0.94rem !important;
        }

        [data-testid="stCheckbox"] label {
            font-size: 0.94rem !important;
        }

        [data-testid="stSlider"] [role="slider"] {
            background: var(--tf-accent) !important;
            border-color: var(--tf-accent) !important;
        }

        .st-key-filter_show_reviewed label:has(input[aria-checked="true"]) > div:first-child {
            background: var(--tf-accent) !important;
        }

        .st-key-filter_show_reviewed label:has(input[aria-checked="true"]) > div:first-child div,
        .st-key-theme_switch label:has(input[aria-checked="true"]) > div:first-child div {
            background: var(--tf-toggle-knob) !important;
        }

        .st-key-theme_switch label:has(input[aria-checked="true"]) > div:first-child {
            background: var(--tf-accent) !important;
        }

        [data-testid="stVerticalBlockBorderWrapper"] {
            background: var(--tf-surface) !important;
            border: 1px solid var(--tf-card-border) !important;
            border-radius: 14px !important;
            box-shadow: var(--tf-shadow);
        }

        [data-testid="stVerticalBlock"]:has(.tf-domain-link):has(.tf-details-spacer):not(:has(.tf-brand)):not(:has(.tf-filters-anchor)):not(.st-key-page_content) {
            background: var(--tf-surface) !important;
            border: 1px solid var(--tf-card-border) !important;
            border-radius: 12px !important;
            box-shadow: var(--tf-shadow) !important;
            margin-bottom: 0.85rem !important;
            padding: 1rem !important;
        }

        [data-testid="stVerticalBlock"]:has(.tf-domain-link):has(.tf-details-spacer):not(:has(.tf-brand)):not(:has(.tf-filters-anchor)):not(.st-key-page_content)
        div[data-testid="stExpander"] {
            background: var(--tf-surface-2) !important;
            border: 1px solid var(--tf-card-border) !important;
            box-shadow: none !important;
        }

        [data-testid="stVerticalBlock"]:has(.tf-domain-link):has(.tf-details-spacer):not(:has(.tf-brand)):not(:has(.tf-filters-anchor)):not(.st-key-page_content)
        div[data-testid="stExpander"] summary {
            background: transparent !important;
            border-bottom: 0 !important;
        }

        div[data-testid="stVerticalBlock"].st-key-page_content div[data-testid="stExpander"]:has(.tf-filters-anchor) {
            background: var(--tf-surface) !important;
            border: 1px solid var(--tf-card-border) !important;
            box-shadow: var(--tf-shadow) !important;
        }

        div[data-testid="stVerticalBlock"].st-key-page_content div[data-testid="stExpander"]:has(.tf-filters-anchor) summary {
            background: var(--tf-surface) !important;
            border-bottom: 1px solid var(--tf-card-border) !important;
        }

        .tf-table-head-wrapper {
            width: 100% !important;
        }

        .tf-table-head-wrapper > div:first-child {
            width: 100% !important;
        }

        .tf-table-head {
            align-items: center;
            background: var(--tf-surface);
            border: 1px solid var(--tf-card-border);
            border-radius: 12px;
            box-sizing: border-box !important;
            color: var(--tf-muted);
            display: grid !important;
            font-size: 0.75rem;
            font-weight: 850;
            gap: 1rem;
            grid-template-columns: 2fr 0.65fr 3.1fr 0.65fr 1.8fr 0.6fr;
            letter-spacing: 0.04em;
            margin: 1.2rem 0 0.55rem;
            padding: 0.78rem 1rem;
            text-transform: uppercase;
            width: 100% !important;
        }

        .stElementContainer:has(.tf-table-head-wrapper) {
            width: 100% !important;
        }

        .stElementContainer:has(.tf-table-head-wrapper) .stMarkdown,
        .stElementContainer:has(.tf-table-head-wrapper) .stMarkdown > div {
            width: 100% !important;
        }

        @media (min-width: 761px) {
            [data-testid="stVerticalBlock"]:has(.tf-domain-link):has(.tf-details-spacer):not(:has(.tf-brand)):not(:has(.tf-filters-anchor)):not(.st-key-page_content)
            [data-testid="stHorizontalBlock"]:has(.tf-domain-link) {
                align-items: center !important;
                display: grid !important;
                gap: 1rem !important;
                grid-template-columns: 2fr 0.65fr 3.1fr 0.65fr 1.8fr 0.6fr !important;
                width: 100% !important;
            }

            [data-testid="stVerticalBlock"]:has(.tf-domain-link):has(.tf-details-spacer):not(:has(.tf-brand)):not(:has(.tf-filters-anchor)):not(.st-key-page_content)
            [data-testid="stHorizontalBlock"]:has(.tf-domain-link) > [data-testid="stColumn"] {
                margin: 0 !important;
                min-width: 0 !important;
                width: 100% !important;
            }
        }

        .tf-domain-cell {
            min-width: 0;
        }

        .tf-details-spacer {
            height: 0.55rem;
        }

        .tf-domain-link {
            color: var(--tf-accent-2) !important;
            font-size: 0.98rem;
            font-weight: 800;
            text-decoration: none;
        }

        .tf-domain-link:hover {
            color: var(--tf-accent) !important;
            text-decoration: underline;
        }

        .tf-domain-pills,
        .tf-pill-row {
            display: flex;
            flex-wrap: wrap;
            gap: 0.35rem;
            margin-top: 0.42rem;
        }

        .tf-pill {
            align-items: center;
            background: var(--tf-pill-bg);
            border: 1px solid var(--tf-pill-border);
            border-radius: 999px;
            color: var(--tf-pill-text);
            display: inline-flex;
            font-size: 0.7rem;
            font-weight: 750;
            line-height: 1;
            padding: 0.34rem 0.55rem;
        }

        .tf-category-pill {
            background: var(--tf-category-bg);
            border-color: var(--tf-category-border);
            color: var(--tf-category-text);
        }

        .tf-model-pill {
            background: var(--tf-model-bg);
            border-color: var(--tf-model-border);
            color: var(--tf-model-text);
        }

        .tf-ranking-pill {
            background: var(--tf-ranking-bg);
            border-color: var(--tf-ranking-border);
            color: var(--tf-ranking-text);
        }

        .tf-country-pill {
            background: var(--tf-country-pill-bg);
            border-color: var(--tf-country-pill-border);
            color: var(--tf-country-pill-text);
        }

        .tf-score {
            border-radius: 999px;
            display: inline-flex;
            font-size: 0.9rem;
            font-weight: 850;
            justify-content: center;
            min-width: 3.15rem;
            padding: 0.45rem 0.7rem;
            border: 2px solid;
        }

        .tf-score-high {
            background: var(--tf-score-high-bg);
            border-color: var(--tf-score-high-border);
            color: var(--tf-score-high-text);
        }

        .tf-score-medium {
            background: var(--tf-score-medium-bg);
            border-color: var(--tf-score-medium-border);
            color: var(--tf-score-medium-text);
        }

        .tf-score-low {
            background: var(--tf-score-low-bg);
            border-color: var(--tf-score-low-border);
            color: var(--tf-score-low-text);
        }

        .tf-summary {
            color: var(--tf-summary);
            font-size: 0.88rem;
            line-height: 1.45;
        }

        .tf-country {
            color: var(--tf-country);
            font-weight: 800;
        }

        .tf-muted {
            color: var(--tf-muted);
        }

        .tf-detail-title {
            color: var(--tf-text);
            font-size: 0.78rem;
            font-weight: 850;
            margin-bottom: 0.45rem;
        }

        .tf-detail-grid {
            display: grid;
            gap: 0.45rem;
        }

        .tf-detail-item {
            display: grid;
            gap: 0.08rem;
        }

        .tf-detail-item span {
            color: var(--tf-muted);
            font-size: 0.75rem;
            font-weight: 760;
        }

        .tf-detail-item strong {
            color: var(--tf-detail-strong);
            font-size: 0.86rem;
            font-weight: 650;
            line-height: 1.4;
        }

        .tf-popover-title {
            font-size: 1rem;
            font-weight: 850;
            margin-bottom: 0.7rem;
        }

        .tf-comment {
            display: grid;
            gap: 0.65rem;
            grid-template-columns: 2px 1fr;
            margin-bottom: 0.85rem;
        }

        .tf-comment-line {
            background: var(--tf-accent);
            border-radius: 999px;
        }

        .tf-comment-body div {
            align-items: baseline;
            display: flex;
            gap: 0.55rem;
        }

        .tf-comment-body span {
            color: var(--tf-muted);
            font-size: 0.75rem;
        }

        .tf-comment-body p {
            color: var(--tf-comment-text);
            font-size: 0.86rem;
            line-height: 1.45;
            margin: 0.25rem 0 0;
        }

        .tf-metric-card {
            background: var(--tf-surface);
            border: 1px solid var(--tf-card-border);
            border-radius: 14px;
            box-shadow: var(--tf-shadow);
            margin-bottom: 0.85rem;
            min-height: 7.15rem;
            padding: 1rem 1.05rem;
        }

        .tf-metric-label {
            color: var(--tf-muted);
            font-size: 0.78rem;
            font-weight: 850;
            letter-spacing: 0.04em;
            text-transform: uppercase;
        }

        .tf-metric-value {
            color: var(--tf-text);
            font-size: 1.85rem;
            font-weight: 900;
            margin-top: 0.5rem;
        }

        .tf-metric-detail {
            color: var(--tf-muted);
            font-size: 0.82rem;
            margin-top: 0.2rem;
        }

        .tf-status-pill {
            border-radius: 999px;
            display: inline-flex;
            font-size: 0.75rem;
            font-weight: 850;
            justify-content: center;
            min-width: 5.5rem;
            padding: 0.36rem 0.65rem;
        }

        .tf-domain-card [data-baseweb="select"] > div {
            background: var(--tf-surface-2) !important;
            border: 1px solid var(--tf-card-border) !important;
            border-radius: 999px !important;
            min-height: 2.2rem !important;
        }

        .tf-domain-card [data-baseweb="select"] > div:hover {
            border-color: var(--tf-accent) !important;
        }

        .tf-domain-card [data-baseweb="select"] div[role="button"] {
            padding: 0.25rem 0.5rem !important;
        }

        .tf-actions-btn {
            background: var(--tf-surface-2) !important;
            border: 1px solid var(--tf-card-border) !important;
            border-radius: 999px !important;
            color: var(--tf-text) !important;
            min-height: 2.2rem !important;
            padding: 0.25rem 0.6rem !important;
            font-weight: 700 !important;
        }

        .tf-actions-btn:hover {
            border-color: var(--tf-accent) !important;
        }

        .tf-status-pending {
            background: var(--tf-status-pending-bg);
            border: 1px solid var(--tf-status-pending-border);
            color: var(--tf-status-pending-text);
        }

        .tf-status-ok,
        .tf-status-completed {
            background: var(--tf-status-ok-bg);
            border: 1px solid var(--tf-status-ok-border);
            color: var(--tf-status-ok-text);
        }

        .tf-status-exists,
        .tf-status-running,
        .tf-status-partial {
            background: var(--tf-status-exists-bg);
            border: 1px solid var(--tf-status-exists-border);
            color: var(--tf-status-exists-text);
        }

        .tf-status-bad,
        .tf-status-failed {
            background: var(--tf-status-bad-bg);
            border: 1px solid var(--tf-status-bad-border);
            color: var(--tf-status-bad-text);
        }

        button[data-testid="stPopoverButton"] {
            background: var(--tf-surface-2) !important;
            border: 1px solid var(--tf-border) !important;
            color: var(--tf-text) !important;
        }

        button[data-testid="stPopoverButton"] * {
            color: var(--tf-text) !important;
        }

        .tf-report-table-head {
            background: var(--tf-table-head);
            border: 1px solid var(--tf-card-border);
            border-radius: 12px;
            color: var(--tf-muted);
            display: grid;
            font-size: 0.75rem;
            font-weight: 850;
            gap: 0.8rem;
            grid-template-columns: 1.2fr 1fr 0.8fr 0.9fr 0.9fr 2fr;
            letter-spacing: 0.04em;
            margin: 1rem 0 0.55rem;
            padding: 0.78rem 1rem;
            text-transform: uppercase;
        }

        .tf-section-title {
            color: var(--tf-text);
            font-size: 1.08rem;
            font-weight: 850;
            margin: 1.1rem 0 0.6rem;
        }

        button[kind="primary"] {
            background: var(--tf-accent) !important;
            border-color: var(--tf-accent) !important;
            color: var(--tf-button-active-text) !important;
            font-weight: 850 !important;
        }

@media (max-width: 760px) {
            :root { --tf-navbar-height: 88px; }
            .block-container {
                padding: 0;
            }

            div[data-testid="stVerticalBlock"]:has(.tf-navbar-anchor) {
                padding: 0.75rem 1rem;
                width: 100vw;
                margin-left: calc(-50vw + 50%);
            }

            .tf-content-wrapper {
                padding: 1rem 1rem 2rem;
            }

            .st-key-main_nav div[data-testid="stPills"] {
                justify-content: flex-start;
            }

            .st-key-main_nav button {
                font-size: 0.85rem !important;
                padding: 0.4rem 0.6rem !important;
            }

            .st-key-theme_switch {
                justify-content: flex-start;
            }

            .tf-page-title {
                font-size: 1.65rem;
            }

            .tf-table-head,
            .tf-report-table-head {
                display: none;
            }

            .tf-metric-card {
                min-height: 0;
            }

            .tf-brand-title {
                font-size: 1rem;
            }

            .tf-brand-subtitle {
                font-size: 0.7rem;
            }
        }

            .tf-topbar {
                align-items: flex-start;
                flex-direction: column;
                gap: 0.85rem;
            }

.st-key-main_nav div[data-testid="stPills"] {
            justify-content: center;
            gap: 0.5rem;
        }

        .st-key-main_nav button {
            background: transparent !important;
            border: none !important;
            border-bottom: 2px solid transparent !important;
            border-radius: 0 !important;
            color: var(--tf-muted) !important;
            font-weight: 600 !important;
            font-size: 0.95rem !important;
            min-height: 2.5rem;
            padding: 0.5rem 1rem !important;
            transition: all 0.2s ease !important;
        }

        .st-key-main_nav button:hover {
            color: var(--tf-text) !important;
            background: var(--tf-surface) !important;
        }

        .st-key-main_nav button[data-testid="stBaseButton-pillsActive"] {
            background: transparent !important;
            border-color: var(--tf-accent) !important;
            color: var(--tf-accent) !important;
        }

            .st-key-theme_switch {
                justify-content: flex-start;
            }

            .tf-page-title {
                font-size: 1.65rem;
            }

            .tf-table-head,
            .tf-report-table-head {
                display: none;
            }

            .tf-metric-card {
                min-height: 0;
            }
        }

        /* Ensure navbar sits flush with the very top and keep content visible */
        html, body, #root, .stApp {
            margin: 0 !important;
            padding: 0 !important;
        }

        :root {
            --tf-navbar-height: 72px;
        }

        div[data-testid="stVerticalBlock"]:has(.tf-navbar-anchor) {
            position: fixed !important;
            top: 0 !important;
            left: 0 !important;
            right: 0 !important;
            width: 100vw !important;
            min-height: var(--tf-navbar-height) !important;
            padding: 0.5rem 2rem !important;
            margin-top: 0 !important;
            z-index: 1100 !important;
            background: var(--tf-surface) !important;
            border-bottom: 1px solid var(--tf-border) !important;
            box-sizing: border-box !important;
            display: flex !important;
            align-items: center !important;
        }

        /* Make inner wrapper stretch and vertically center contents */
        div[data-testid="stVerticalBlock"]:has(.tf-navbar-anchor) > div {
            height: 100% !important;
            display: flex !important;
            align-items: center !important;
            gap: 1rem;
            padding: 0 !important;
            box-sizing: border-box !important;
        }

        /* Ensure brand, nav and theme widgets are vertically centered */
        div[data-testid="stVerticalBlock"]:has(.tf-navbar-anchor) .tf-brand,
        div[data-testid="stVerticalBlock"]:has(.tf-navbar-anchor) .st-key-main_nav,
        div[data-testid="stVerticalBlock"]:has(.tf-navbar-anchor) .st-key-theme_switch {
            height: 100% !important;
            display: flex !important;
            align-items: center !important;
        }

        div[data-testid="stVerticalBlock"]:has(.tf-navbar-anchor) img {
            max-height: calc(var(--tf-navbar-height) - 18px) !important;
            height: auto !important;
        }

        /* Ensure page content is pushed below the fixed navbar */
        .tf-content-wrapper,
        div[data-testid="stVerticalBlock"].st-key-page_content {
            padding-top: 2.25rem !important;
        }

        @media (min-width: 761px) {
            .tf-content-wrapper,
            div[data-testid="stVerticalBlock"].st-key-page_content {
                padding-left: clamp(3rem, 4vw, 3.75rem) !important;
                padding-right: clamp(3rem, 4vw, 3.75rem) !important;
            }
        }

        @media (max-width: 760px) {
            .tf-content-wrapper,
            div[data-testid="stVerticalBlock"].st-key-page_content {
                padding-left: 1.15rem !important;
                padding-right: 1.15rem !important;
                padding-top: 1.35rem !important;
            }
        }

        html,
        body {
            overflow-x: hidden !important;
            overflow-y: auto !important;
        }

        [data-testid="stAppViewContainer"],
        [data-testid="stMain"],
        .stMain {
            overflow-x: hidden !important;
            overflow-y: auto !important;
        }

        div[data-testid="stVerticalBlock"]:has(.tf-navbar-anchor) {
            background: transparent !important;
            border-bottom: 0 !important;
            display: block !important;
            margin: 0 !important;
            min-height: 0 !important;
            padding: 0 !important;
            position: static !important;
            width: auto !important;
        }

        div[data-testid="stVerticalBlock"]:has(.tf-navbar-anchor) > div {
            align-items: stretch !important;
            display: block !important;
            gap: 0 !important;
            height: auto !important;
        }

        div[data-testid="stVerticalBlock"].st-key-top_navbar {
            align-items: center !important;
            background: var(--tf-surface) !important;
            border: 0 !important;
            border-bottom: 1px solid var(--tf-border) !important;
            border-radius: 0 !important;
            box-sizing: border-box !important;
            display: flex !important;
            left: 0 !important;
            margin: 0 !important;
            min-height: var(--tf-navbar-height) !important;
            padding: 0.5rem 2rem !important;
            position: fixed !important;
            right: 0 !important;
            box-shadow: 0 1px 0 var(--tf-border) !important;
            top: 0 !important;
            width: 100vw !important;
            z-index: 1100 !important;
        }

        div[data-testid="stVerticalBlock"].st-key-top_navbar,
        div[data-testid="stVerticalBlock"].st-key-top_navbar > div,
        div[data-testid="stVerticalBlock"].st-key-top_navbar [data-testid="stLayoutWrapper"],
        div[data-testid="stVerticalBlock"].st-key-top_navbar [data-testid="stHorizontalBlock"],
        div[data-testid="stVerticalBlock"].st-key-top_navbar [data-testid="column"],
        div[data-testid="stVerticalBlock"].st-key-top_navbar [data-testid="stElementContainer"] {
            border-radius: 0 !important;
        }

        div[data-testid="stVerticalBlock"].st-key-top_navbar > div,
        div[data-testid="stVerticalBlock"].st-key-top_navbar [data-testid="stLayoutWrapper"],
        div[data-testid="stVerticalBlock"].st-key-top_navbar [data-testid="stHorizontalBlock"] {
            align-items: center !important;
            background: transparent !important;
            border: 0 !important;
            box-sizing: border-box !important;
            display: flex !important;
            gap: 1rem;
            height: 100% !important;
            width: 100% !important;
        }

        div[data-testid="stVerticalBlock"].st-key-top_navbar [data-testid="column"] {
            background: transparent !important;
            border: 0 !important;
            box-shadow: none !important;
            padding: 0 !important;
        }

        @media (min-width: 761px) {
            div[data-testid="stVerticalBlock"].st-key-top_navbar .st-key-main_nav {
                margin-left: auto !important;
                margin-right: auto !important;
            }

            div[data-testid="stVerticalBlock"].st-key-top_navbar [data-testid="stColumn"]:has(.st-key-theme_switch) {
                align-items: center !important;
                display: flex !important;
                justify-content: flex-end !important;
            }

            div[data-testid="stVerticalBlock"].st-key-top_navbar [data-testid="stColumn"]:has(.st-key-theme_switch) > [data-testid="stVerticalBlock"],
            div[data-testid="stVerticalBlock"].st-key-top_navbar .st-key-theme_switch {
                align-items: center !important;
                justify-content: flex-end !important;
                margin-left: auto !important;
            }
        }
        </style>
        """.replace("__THEME_VARS__", _theme_vars(theme_name)),
        unsafe_allow_html=True,
    )


def ensure_ui_state() -> None:
    query_theme = _theme_from_query_params()

    if "active_tab" not in st.session_state:
        st.session_state.active_tab = NAV_ITEMS[0]

    if "theme_switch" not in st.session_state:
        st.session_state.theme_switch = query_theme != "Light"
        st.session_state.theme_query_applied = query_theme
    elif query_theme and st.session_state.get("theme_query_applied") != query_theme:
        st.session_state.theme_switch = query_theme == "Dark"
        st.session_state.theme_query_applied = query_theme

    st.session_state.theme_mode = "Dark" if st.session_state.theme_switch else "Light"


def render_navbar() -> str:
    ensure_ui_state()

    project_root = Path(__file__).resolve().parent.parent
    logo_path = project_root / "assets" / "logo.png"

    brand_col, nav_col, theme_col = st.columns([1, 1, 1], vertical_alignment="center")

    with brand_col:
        if logo_path.exists():
            col_logo, col_title = st.columns([0.25, 1], gap="small")
            with col_logo:
                st.image(str(logo_path), width=42)
            with col_title:
                st.markdown(
                    """
                    <div class="tf-brand-title">TrendingFounder</div>
                    <div class="tf-brand-subtitle">Domain Discovery Dashboard</div>
                    """,
                    unsafe_allow_html=True,
                )
        else:
            st.markdown(
                """
                <div class="tf-brand">
                    <div class="tf-brand-mark">TF</div>
                    <div>
                        <div class="tf-brand-title">TrendingFounder</div>
                        <div class="tf-brand-subtitle">Domain Discovery Dashboard</div>
                    </div>
                </div>
                """,
                unsafe_allow_html=True,
            )
    selected = nav_col.pills(
        "Navigation",
        NAV_ITEMS,
        default=st.session_state.active_tab,
        key="main_nav",
        label_visibility="collapsed",
    )
    dark_mode = theme_col.toggle("Dark mode", key="theme_switch")
    st.session_state.theme_mode = "Dark" if dark_mode else "Light"

    if selected:
        st.session_state.active_tab = selected
    return st.session_state.active_tab


def render_page_header(title: str, subtitle: str) -> None:
    st.markdown(
        f"""
        <div class="tf-page-header">
            <div class="tf-page-title">{escape(title)}</div>
            <div class="tf-page-subtitle">{escape(subtitle)}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def on_status_change(domain_id: str, new_status: str) -> None:
    repo = DomainRepository()
    repo.update_review_status(domain_id, ReviewStatus(new_status))
    st.rerun()


def on_add_comment(domain_id: str, author: str, message: str) -> None:
    repo = CommentRepository()
    repo.add_comment(domain_id, author, message)
    st.rerun()


def _session_option(key: str, options: list[str], default: str) -> str:
    value = st.session_state.get(key, default)
    return value if value in options else default


def _session_int(key: str, default: int = 0, minimum: int = 0, maximum: int = 200) -> int:
    try:
        value = int(st.session_state.get(key, default))
    except (TypeError, ValueError):
        value = default
    return max(minimum, min(value, maximum))


def current_filter_values() -> dict:
    """Read filter widget state before rendering widgets to avoid header reflow."""
    return {
        "search_query": str(st.session_state.get("filter_search", "")),
        "status_filter": _session_option("filter_status", STATUS_FILTER_OPTIONS, STATUS_FILTER_OPTIONS[0]),
        "category_filter": _session_option("filter_category", CATEGORY_FILTER_OPTIONS, CATEGORY_FILTER_OPTIONS[0]),
        "show_reviewed": bool(st.session_state.get("filter_show_reviewed", True)),
        "sort_by": _session_option("filter_sort", SORT_OPTIONS, SORT_OPTIONS[0]),
        "min_score": _session_int("filter_min_score"),
    }


def render_collected_data_page() -> None:
    filters = current_filter_values()

    df = load_today_data(
        show_reviewed=filters["show_reviewed"],
        sort_by=filters["sort_by"],
        min_score=filters["min_score"],
        search_query=filters["search_query"],
        status_filter=filters["status_filter"],
        category_filter=filters["category_filter"],
    )
    domain_count = 0 if df.empty else len(df)
    render_page_header(
        "Collected Data",
        f"{domain_count} domains found · Best score today across the world",
    )
    render_filters(show_reviewed_default=filters["show_reviewed"], expanded=True)

    comments_data = load_comments(df["id"].tolist()) if not df.empty and "id" in df.columns else {}
    render_domain_table(
        df,
        on_status_change=on_status_change,
        on_add_comment=on_add_comment,
        comments_data=comments_data,
    )


def _status_pill(status: str) -> str:
    normalized = (status or "pending").lower()
    return f"<span class='tf-status-pill tf-status-{escape(normalized)}'>{escape(normalized)}</span>"


def _is_missing(value) -> bool:
    if value is None:
        return True
    if isinstance(value, float):
        return isnan(value)
    return str(value).strip().lower() in ("", "nan", "none")


def _display_value(value, default: str = "N/A") -> str:
    return default if _is_missing(value) else str(value)


def _int_value(value) -> int:
    if _is_missing(value):
        return 0
    try:
        return int(float(value))
    except (TypeError, ValueError):
        return 0


def render_country_status_table(country_df) -> None:
    st.markdown(
        """
        <div class="tf-report-table-head">
            <span>Country</span>
            <span>Status</span>
            <span>Items found</span>
            <span>New domains</span>
            <span>Duplicates</span>
            <span>Error</span>
        </div>
        """,
        unsafe_allow_html=True,
    )

    if country_df is None or country_df.empty:
        st.info("No crawl data available for today.")
        return

    if "country_code" in country_df.columns:
        country_df = country_df[~country_df["country_code"].isna()]

    if country_df.empty:
        st.info("No country-level crawl rows available for today yet.")
        return

    for _, row in country_df.iterrows():
        country_code = _display_value(row.get("country_code"))
        country_name = "" if _is_missing(row.get("country_name")) else str(row.get("country_name"))
        country_label = f"{country_code} · {country_name}" if country_name else str(country_code)

        with st.container(border=True):
            cols = st.columns([1.2, 1, 0.8, 0.9, 0.9, 2], gap="medium", vertical_alignment="center")
            cols[0].markdown(f"**{escape(str(country_label))}**")
            cols[1].markdown(_status_pill(_display_value(row.get("country_status"), "pending")), unsafe_allow_html=True)
            cols[2].write(_int_value(row.get("items_found")))
            cols[3].write(_int_value(row.get("new_domains")))
            cols[4].write(_int_value(row.get("duplicate_domains")))
            error_message = "" if _is_missing(row.get("error_message")) else str(row.get("error_message"))
            cols[5].markdown(f"<span class='tf-muted'>{escape(error_message or 'None')}</span>", unsafe_allow_html=True)


def render_reports_page() -> None:
    stats = load_stats()
    country_df = load_country_progress()
    render_page_header("Reports", "Crawl metrics, enrichment progress, and country-by-country status")

    render_metrics_cards(
        {
            "countries_ran": stats.get("countries_completed", 0),
            "countries_total": stats.get("countries_total", 0),
            "new_domains": stats.get("new_domains_count", 0),
            "duplicates": stats.get("duplicate_domains_count", 0),
            "llm_processed": stats.get("llm_processed_count", 0),
            "high_score_today": load_high_score_count(),
            "reviewed_today": load_reviewed_count(),
        }
    )

    st.markdown("<div class='tf-section-title'>Daily Crawl Progress</div>", unsafe_allow_html=True)
    render_progress_bar(stats.get("countries_completed", 0), stats.get("countries_total", 0))

    if stats.get("status"):
        st.markdown(_status_pill(str(stats["status"])), unsafe_allow_html=True)

    st.markdown("<div class='tf-section-title'>Country Status</div>", unsafe_allow_html=True)
    render_country_status_table(country_df)


def _sync_theme_preference(theme_name: str) -> None:
    theme_name = "Light" if theme_name == "Light" else "Dark"
    components.html(
        f"""
        <script>
        (function() {{
            var parentWindow = window.parent;
            var currentTheme = "{theme_name}";
            var storageKey = "{THEME_STORAGE_KEY}";
            var queryKey = "{THEME_QUERY_PARAM}";
            var url = new URL(parentWindow.location.href);
            var queryTheme = (url.searchParams.get(queryKey) || "").toLowerCase();
            var savedTheme = parentWindow.localStorage.getItem(storageKey);
            var savedQueryTheme = savedTheme === "Light" ? "light" : savedTheme === "Dark" ? "dark" : "";

            if (!queryTheme && savedQueryTheme && savedTheme !== currentTheme) {{
                url.searchParams.set(queryKey, savedQueryTheme);
                parentWindow.location.replace(url.toString());
                return;
            }}

            parentWindow.localStorage.setItem(storageKey, currentTheme);

            if (queryTheme !== currentTheme.toLowerCase()) {{
                url.searchParams.set(queryKey, currentTheme.toLowerCase());
                parentWindow.history.replaceState(null, "", url.toString());
            }}
        }})();
        </script>
        """,
        height=0,
    )


def render() -> None:
    st.set_page_config(
        page_title="TrendingFounder",
        page_icon="TF",
        layout="wide",
        initial_sidebar_state="collapsed",
    )
    ensure_ui_state()
    theme_name = st.session_state.get("theme_mode", "Dark")
    inject_styles(theme_name)

    _sync_theme_preference(theme_name)

    with st.container(key="top_navbar"):
        active_tab = render_navbar()

    with st.container(key="page_content"):
        if active_tab == "Reports":
            render_reports_page()
        else:
            render_collected_data_page()


if __name__ == "__main__":
    render()
