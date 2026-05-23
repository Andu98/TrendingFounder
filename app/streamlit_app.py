# ruff: noqa: E402

import base64
import sys
from concurrent.futures import ThreadPoolExecutor
from datetime import date
from html import escape
from math import ceil, isnan
from pathlib import Path

import pandas as pd
import streamlit as st

# Add project root to sys.path so we can import from src/
project_root = Path(__file__).resolve().parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from app.components.domain_table import render_domain_table
from app.components.filters import _default_date_range, render_filters
from app.components.metrics_cards import render_metrics_cards, render_progress_bar
from app.data_loader import (
    CATEGORY_FILTER_OPTIONS,
    DEFAULT_PAGE_SIZE,
    OPPORTUNITY_TYPE_OPTIONS,
    PAGE_SIZE_OPTIONS,
    SORT_OPTIONS,
    STATUS_FILTER_OPTIONS,
    clear_dashboard_caches,
    load_collected_data,
    load_comments,
    load_country_progress,
    load_github_crawl_stats,
    load_github_language_options,
    load_high_score_count,
    load_new_github_repositories,
    load_reviewed_count,
    load_stats,
    mark_github_repo_seen,
    mark_github_repos_seen,
    update_github_repo_notes,
    update_github_repo_review_status,
)
from src.config.constants import COUNTRY_CODES, GitHubRepoReviewStatus, ReviewStatus
from src.db.repositories import CommentRepository, DomainRepository
from src.integrations.github_actions import (
    GitHubActionsError,
    list_recent_runs,
    trigger_workflow,
)

NAV_ITEMS = ["Collected Data", "GitHub Opencode", "Reports"]
THEME_QUERY_PARAM = "theme"
THEME_STORAGE_KEY = "tf_theme"
_STATUS_UPDATE_EXECUTOR = ThreadPoolExecutor(max_workers=2, thread_name_prefix="domain-status-update")

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
        "shadow": "0 12px 36px rgba(2, 13, 17, 0.2)",
        "shadow_strong": "0 16px 44px rgba(2, 13, 17, 0.24)",
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

        html,
        body,
        #root,
        .stApp {
            background: var(--tf-bg) !important;
            border-radius: 0 !important;
            color: var(--tf-text);
            overflow-x: hidden;
            overflow-y: auto !important;
        }

        .stApp > div,
        .stApp > div > div,
        .stApp > div > div > div,
        .block-container,
        .block-container > div {
            border-radius: 0 !important;
        }

        .st-emotion-cache-tn0cau {
            gap: 0 !important;
        }

        .block-container {
            max-width: 100%;
            padding: 0;
        }

        [data-testid="stSidebar"],
        [data-testid="collapsedControl"],
        [data-testid="stHeader"],
        button[data-testid="stExpandSidebarButton"],
        button[data-testid="stBaseButton-headerNoPadding"],
        button[data-testid="stBaseButton-header"],
        button[data-testid="stMainMenuButton"] {
            display: none !important;
        }

        h1, h2, h3, p, span, label {
            color: var(--tf-text);
        }

        div[data-testid="stVerticalBlock"].st-key-top_navbar {
            background: var(--tf-surface) !important;
            border-bottom: 1px solid var(--tf-border) !important;
            border-radius: 0 !important;
            box-sizing: border-box !important;
            margin: 0 !important;
            padding: 0.65rem clamp(1.25rem, 3vw, 2.5rem) !important;
            position: static !important;
            width: 100% !important;
            z-index: auto !important;
        }

        div[data-testid="stVerticalBlock"].st-key-top_navbar > div,
        div[data-testid="stVerticalBlock"].st-key-top_navbar [data-testid="stLayoutWrapper"],
        div[data-testid="stVerticalBlock"].st-key-top_navbar [data-testid="stHorizontalBlock"],
        div[data-testid="stVerticalBlock"].st-key-top_navbar [data-testid="stColumn"],
        div[data-testid="stVerticalBlock"].st-key-top_navbar [data-testid="stElementContainer"] {
            background: transparent !important;
            border: 0 !important;
            border-radius: 0 !important;
            box-shadow: none !important;
        }

        div[data-testid="stVerticalBlock"].st-key-page_content {
            box-sizing: border-box;
            margin: 0 auto;
            max-width: 1360px;
            padding: 2.25rem clamp(3rem, 4vw, 3.75rem) 3rem;
            width: 100%;
        }

        .st-key-mobile_navbar {
            display: none !important;
        }

        .tf-brand {
            align-items: center;
            display: flex;
            gap: 0.8rem;
            min-width: 0;
        }

        .tf-brand-logo,
        .tf-brand-mark {
            align-items: center;
            background: linear-gradient(135deg, var(--tf-accent), var(--tf-accent-2));
            border-radius: 999px;
            box-shadow: 0 12px 35px rgba(24, 196, 199, 0.24);
            color: var(--tf-brand-mark-text);
            display: inline-flex;
            flex: 0 0 auto;
            font-size: 0.75rem;
            font-weight: 900;
            height: 2.65rem;
            justify-content: center;
            object-fit: cover;
            width: 2.65rem;
        }

        .tf-brand-title {
            color: var(--tf-text);
            font-size: 1.18rem;
            font-weight: 850;
            line-height: 1.1;
            white-space: nowrap;
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

        .st-key-desktop_navbar [data-testid="stHorizontalBlock"] {
            align-items: center !important;
            display: grid !important;
            gap: clamp(1rem, 3vw, 2rem) !important;
            grid-template-columns: minmax(0, 1fr) auto minmax(0, 1fr) !important;
            width: 100% !important;
        }

        .st-key-desktop_navbar [data-testid="stColumn"] {
            min-width: 0 !important;
            width: 100% !important;
        }

        .st-key-desktop_navbar [data-testid="stColumn"]:has(.st-key-desktop_main_nav) {
            justify-self: center !important;
            width: auto !important;
        }

        .st-key-desktop_main_nav div[data-testid="stPills"],
        .st-key-mobile_main_nav div[data-testid="stPills"] {
            justify-content: center;
        }

        .st-key-desktop_main_nav button,
        .st-key-mobile_main_nav button {
            background: var(--tf-surface) !important;
            border: 1px solid var(--tf-border) !important;
            border-radius: 999px !important;
            color: var(--tf-muted) !important;
            font-weight: 750 !important;
            min-height: 2.25rem;
        }

        .st-key-desktop_main_nav button[data-testid="stBaseButton-pillsActive"],
        .st-key-mobile_main_nav button[data-testid="stBaseButton-pillsActive"] {
            background: var(--tf-accent) !important;
            border-color: var(--tf-accent) !important;
            color: var(--tf-button-active-text) !important;
        }

        .st-key-desktop_theme_switch,
        .st-key-mobile_theme_switch {
            display: flex;
            justify-content: flex-end;
            margin-left: auto;
            width: 100%;
        }

        .st-key-desktop_theme_switch > div,
        .st-key-mobile_theme_switch > div,
        .st-key-desktop_theme_switch label,
        .st-key-mobile_theme_switch label {
            justify-content: flex-end !important;
            width: 100% !important;
        }

        .st-key-desktop_theme_switch label,
        .st-key-mobile_theme_switch label,
        .st-key-filter_show_reviewed label {
            color: var(--tf-muted) !important;
            font-size: 0.86rem !important;
            font-weight: 750 !important;
            gap: 0.45rem;
            white-space: nowrap;
        }

        .st-key-desktop_theme_switch label > div:first-child,
        .st-key-mobile_theme_switch label > div:first-child,
        .st-key-filter_show_reviewed label > div:first-child {
            background: var(--tf-toggle-track) !important;
            border: 1px solid var(--tf-card-border) !important;
        }

        .st-key-desktop_theme_switch label > div:first-child div,
        .st-key-mobile_theme_switch label > div:first-child div,
        .st-key-filter_show_reviewed label > div:first-child div {
            background: var(--tf-toggle-knob) !important;
        }

        .st-key-desktop_theme_switch p,
        .st-key-mobile_theme_switch p,
        .st-key-filter_show_reviewed p {
            color: var(--tf-text) !important;
            font-weight: 750 !important;
        }

        .st-key-desktop_theme_switch label:has(input[aria-checked="true"]) > div:first-child,
        .st-key-mobile_theme_switch label:has(input[aria-checked="true"]) > div:first-child,
        .st-key-filter_show_reviewed label:has(input[aria-checked="true"]) > div:first-child {
            background: var(--tf-accent) !important;
        }

        div[data-testid="stExpander"] {
            background: var(--tf-surface);
            border: 1px solid var(--tf-card-border);
            border-radius: 8px;
            box-shadow: var(--tf-shadow-strong);
            overflow: hidden;
        }

        div[data-testid="stExpander"] summary {
            background: var(--tf-surface-2) !important;
            border-bottom: 1px solid var(--tf-card-border);
            color: var(--tf-text);
            font-weight: 750;
        }

        div[data-testid="stExpander"]:has(.tf-filters-anchor),
        div[data-testid="stVerticalBlock"].st-key-page_content div[data-testid="stExpander"]:has(.tf-filters-anchor) {
            background: var(--tf-surface) !important;
            border: 1px solid var(--tf-card-border) !important;
            box-shadow: var(--tf-shadow) !important;
        }

        div[data-testid="stExpander"]:has(.tf-filters-anchor) summary {
            background: var(--tf-surface) !important;
            border-bottom: 1px solid var(--tf-card-border) !important;
        }

        div[data-testid="stExpander"]:has(.tf-filters-anchor) [data-testid="stHorizontalBlock"] {
            align-items: end !important;
        }

        div[data-testid="stExpander"]:has(.tf-filters-anchor) label {
            min-height: 1.35rem;
        }

        div[data-testid="stExpander"]:has(.tf-filters-anchor) [data-testid="stDateInput"] input,
        div[data-testid="stExpander"]:has(.tf-filters-anchor) [data-testid="stTextInput"] input,
        div[data-testid="stExpander"]:has(.tf-filters-anchor) [data-baseweb="select"] > div {
            min-height: 2.75rem !important;
        }

        div[data-testid="stExpander"]:has(.tf-filters-anchor) .st-key-filter_show_reviewed {
            padding-bottom: 0.42rem;
        }

        .tf-status-filter-label {
            color: var(--tf-muted);
            font-size: 0.78rem;
            font-weight: 850;
            letter-spacing: 0.04em;
            margin: 0.9rem 0 0.3rem;
            text-transform: uppercase;
        }

        .st-key-filter_status_pending label,
        .st-key-filter_status_ok label,
        .st-key-filter_status_exists label,
        .st-key-filter_status_bad label {
            color: var(--tf-text) !important;
            font-size: 0.86rem !important;
            font-weight: 750 !important;
            gap: 0.45rem;
            white-space: nowrap;
        }

        [data-testid="stTextInput"] {
            min-height: 48px;
        }

        [data-testid="stTextInput"] input,
        [data-testid="stTextArea"] textarea,
        [data-baseweb="select"] > div {
            background: var(--tf-input-bg) !important;
            border: 1px solid var(--tf-border) !important;
            box-shadow: none !important;
            color: var(--tf-text) !important;
            outline: none !important;
        }

        [data-testid="stTextInput"] input:focus,
        [data-testid="stTextArea"] textarea:focus,
        [data-baseweb="select"] > div:focus-within {
            border-color: var(--tf-accent) !important;
            box-shadow: 0 0 0 3px color-mix(in srgb, var(--tf-accent) 18%, transparent) !important;
        }

        [data-testid="stTextInput"] input,
        [data-testid="stTextArea"] textarea {
            -webkit-text-fill-color: var(--tf-text) !important;
            caret-color: var(--tf-accent) !important;
        }

        [data-testid="stTextInput"] input::placeholder,
        [data-testid="stTextArea"] textarea::placeholder {
            -webkit-text-fill-color: var(--tf-placeholder) !important;
            color: var(--tf-placeholder) !important;
            opacity: 1 !important;
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

        [data-testid="stVerticalBlockBorderWrapper"] {
            background: var(--tf-surface) !important;
            border: 1px solid var(--tf-card-border) !important;
            border-radius: 8px !important;
            box-shadow: var(--tf-shadow);
        }

        [data-testid="stVerticalBlockBorderWrapper"]:has(.tf-domain-link) {
            background: transparent !important;
            border: 0 !important;
            box-shadow: none !important;
            padding: 0 !important;
        }

        .tf-table-head-wrapper {
            overflow-x: auto;
            width: 100% !important;
        }

        .tf-table-head {
            align-items: center;
            background: var(--tf-surface);
            border: 1px solid var(--tf-card-border);
            border-radius: 8px;
            box-sizing: border-box !important;
            color: var(--tf-muted);
            display: grid !important;
            font-size: 0.75rem;
            font-weight: 850;
            gap: 1rem;
            grid-template-columns: 2fr 1.7fr 0.65fr 3.1fr 0.65fr 0.85fr;
            letter-spacing: 0.04em;
            margin: 1.2rem 0 0.55rem;
            padding: 0.78rem 1rem;
            text-transform: uppercase;
            width: 100% !important;
        }

        .tf-table-head-mobile,
        .tf-mobile-field-label {
            display: none !important;
        }

        .stElementContainer:has(.tf-mobile-widget-label) {
            display: none !important;
        }

        .stElementContainer:has(.tf-table-head-wrapper),
        .stElementContainer:has(.tf-table-head-wrapper) .stMarkdown,
        .stElementContainer:has(.tf-table-head-wrapper) .stMarkdown > div {
            width: 100% !important;
        }

        [data-testid="stVerticalBlock"]:has(
            > [data-testid="stLayoutWrapper"] > [data-testid="stHorizontalBlock"] .tf-domain-link
        ) {
            background: var(--tf-surface) !important;
            border: 1px solid var(--tf-card-border) !important;
            border-radius: 8px !important;
            box-shadow: var(--tf-shadow) !important;
            margin-bottom: 0.85rem !important;
            overflow-x: auto !important;
            overflow-y: visible !important;
            padding: 1rem !important;
            transition: border-color 180ms ease, transform 180ms ease;
        }

        [data-testid="stVerticalBlock"]:has(
            > [data-testid="stLayoutWrapper"] > [data-testid="stHorizontalBlock"] .tf-domain-link
        ):hover {
            border-color: var(--tf-accent) !important;
            transform: translateY(-1px);
        }

        [data-testid="stHorizontalBlock"]:has(.tf-domain-link) {
            align-items: center !important;
            display: grid !important;
            gap: 1rem !important;
            grid-template-columns: 2fr 1.7fr 0.65fr 3.1fr 0.65fr 0.85fr !important;
            width: 100% !important;
        }

        [data-testid="stHorizontalBlock"]:has(.tf-domain-link) > [data-testid="stColumn"] {
            flex: unset !important;
            margin: 0 !important;
            max-width: none !important;
            min-width: 0 !important;
            width: 100% !important;
        }

        [data-testid="stVerticalBlock"]:has(
            > [data-testid="stLayoutWrapper"] > [data-testid="stHorizontalBlock"] .tf-domain-link
        )
        div[data-testid="stExpander"] {
            background: transparent !important;
            border: 0 !important;
            border-top: 1px solid var(--tf-border) !important;
            border-radius: 0 !important;
            box-shadow: none !important;
        }

        [data-testid="stVerticalBlock"]:has(
            > [data-testid="stLayoutWrapper"] > [data-testid="stHorizontalBlock"] .tf-domain-link
        )
        div[data-testid="stExpander"] summary {
            background: transparent !important;
            border-bottom: 0 !important;
        }

        .tf-domain-cell {
            min-width: 0;
        }

        .tf-domain-primary {
            min-width: 0;
        }

        .tf-score-mobile {
            display: none;
        }

        .tf-domain-url-mobile,
        .tf-summary-mobile {
            display: none;
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

        .tf-giant-pill {
            background: var(--tf-status-bad-bg);
            border-color: var(--tf-status-bad-border);
            color: var(--tf-status-bad-text);
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
            border: 2px solid;
            border-radius: 999px;
            display: inline-flex;
            font-size: 0.9rem;
            font-weight: 850;
            justify-content: center;
            min-width: 3.15rem;
            padding: 0.45rem 0.7rem;
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

        .tf-empty-state {
            background: var(--tf-surface);
            border: 1px dashed var(--tf-card-border);
            border-radius: 8px;
            box-shadow: var(--tf-shadow);
            margin: 1rem 0;
            padding: 1.25rem;
        }

        .tf-empty-state-title {
            color: var(--tf-text);
            font-size: 1rem;
            font-weight: 850;
            margin-bottom: 0.35rem;
        }

        .tf-empty-state-text {
            color: var(--tf-muted);
            font-size: 0.9rem;
            line-height: 1.45;
            max-width: 65ch;
        }

        .tf-opportunity-panel {
            background: var(--tf-surface-2);
            border: 1px solid var(--tf-border);
            border-radius: 8px;
            display: grid;
            gap: 0.9rem;
            padding: 0.95rem;
        }

        .tf-opportunity-kpis {
            display: grid;
            gap: 0.65rem;
            grid-template-columns: repeat(4, minmax(0, 1fr));
        }

        .tf-opportunity-kpi {
            background: var(--tf-surface);
            border: 1px solid var(--tf-border);
            border-radius: 8px;
            display: grid;
            gap: 0.28rem;
            min-width: 0;
            padding: 0.72rem;
        }

        .tf-opportunity-kpi span,
        .tf-opportunity-copy span {
            color: var(--tf-muted);
            font-size: 0.72rem;
            font-weight: 850;
            letter-spacing: 0.04em;
            text-transform: uppercase;
        }

        .tf-opportunity-kpi strong {
            color: var(--tf-detail-strong);
            font-size: 0.95rem;
            font-weight: 800;
            line-height: 1.25;
            min-width: 0;
        }

        .tf-opportunity-copy {
            display: grid;
            gap: 0.7rem;
        }

        .tf-opportunity-copy div {
            display: grid;
            gap: 0.18rem;
        }

        .tf-opportunity-copy strong {
            color: var(--tf-detail-strong);
            font-size: 0.9rem;
        }

        .tf-opportunity-copy p {
            color: var(--tf-summary);
            font-size: 0.88rem;
            line-height: 1.45;
            margin: 0;
        }

        .tf-notes-panel {
            display: grid;
            gap: 0.6rem;
        }

        .tf-notes-header {
            align-items: center;
            border-bottom: 1px solid var(--tf-border);
            display: flex;
            gap: 0.75rem;
            justify-content: space-between;
            margin: 0 0 0.5rem;
            padding-bottom: 0.5rem;
        }

        .tf-notes-title {
            color: var(--tf-text);
            font-size: 0.88rem;
            font-weight: 850;
            line-height: 1.2;
        }

        .tf-notes-subtitle {
            color: var(--tf-muted);
            font-size: 0.72rem;
            font-weight: 600;
            line-height: 1.3;
            margin-top: 0.08rem;
            overflow-wrap: anywhere;
            max-width: 220px;
            overflow: hidden;
            text-overflow: ellipsis;
            white-space: nowrap;
        }

        .tf-notes-header > span {
            align-items: center;
            background: var(--tf-pill-bg);
            border: 1px solid var(--tf-pill-border);
            border-radius: 999px;
            color: var(--tf-pill-text);
            display: flex;
            font-size: 0.68rem;
            font-weight: 850;
            height: 1.5rem;
            justify-content: center;
            min-width: 1.5rem;
            padding: 0 0.4rem;
            flex-shrink: 0;
        }

        .tf-notes-list {
            display: grid;
            gap: 0.45rem;
            max-height: 14rem;
            overflow-y: auto;
            padding-right: 0.15rem;
        }

        .tf-notes-list::-webkit-scrollbar {
            width: 4px;
        }

        .tf-notes-list::-webkit-scrollbar-track {
            background: transparent;
        }

        .tf-notes-list::-webkit-scrollbar-thumb {
            background: var(--tf-border);
            border-radius: 4px;
        }

        .tf-note {
            background: var(--tf-surface-2);
            border: 1px solid var(--tf-border);
            border-radius: 6px;
            display: grid;
            gap: 0.28rem;
            padding: 0.5rem 0.6rem;
        }

        .tf-note-meta {
            align-items: baseline;
            display: flex;
            gap: 0.4rem;
            justify-content: space-between;
        }

        .tf-note-meta strong {
            color: var(--tf-detail-strong);
            font-size: 0.76rem;
            font-weight: 800;
        }

        .tf-note-meta span {
            color: var(--tf-muted);
            font-size: 0.65rem;
            white-space: nowrap;
        }

        .tf-note p {
            color: var(--tf-comment-text);
            font-size: 0.8rem;
            line-height: 1.4;
            margin: 0;
            overflow-wrap: anywhere;
        }

        .tf-note-empty {
            background: var(--tf-surface-2);
            border: 1px dashed var(--tf-border);
            border-radius: 6px;
            color: var(--tf-muted);
            font-size: 0.78rem;
            line-height: 1.4;
            padding: 0.6rem 0.7rem;
        }

        .tf-note-composer {
            display: grid;
            gap: 0.45rem;
        }

        .tf-note-composer-row {
            display: grid;
            gap: 0.4rem;
            grid-template-columns: 1fr 2fr;
        }

        .tf-note-composer-title {
            color: var(--tf-text);
            font-size: 0.76rem;
            font-weight: 800;
            margin: 0;
            text-transform: uppercase;
            letter-spacing: 0.03em;
        }

        .tf-metric-card {
            background: var(--tf-surface);
            border: 1px solid var(--tf-card-border);
            border-radius: 8px;
            box-shadow: var(--tf-shadow);
            margin-bottom: 0.85rem;
            min-height: 7.2rem;
            height: 7.2rem;
            padding: 1rem 1.05rem;
            display: flex;
            flex-direction: column;
            justify-content: space-between;
            overflow: hidden;
        }

        .tf-metric-topline {
            align-items: flex-start;
            display: flex;
            flex-direction: column;
            gap: 0.3rem;
        }

        .tf-metric-label {
            color: var(--tf-muted);
            font-size: 0.72rem;
            font-weight: 850;
            letter-spacing: 0.04em;
            text-transform: uppercase;
            white-space: nowrap;
            overflow: hidden;
            text-overflow: ellipsis;
            max-width: 100%;
        }

        .tf-metric-value {
            color: var(--tf-text);
            font-size: 1.28rem;
            font-weight: 900;
            line-height: 1.1;
            text-align: left;
            white-space: nowrap;
            overflow: hidden;
            text-overflow: ellipsis;
            max-width: 100%;
        }

        .tf-metric-detail {
            color: var(--tf-muted);
            font-size: 0.78rem;
            margin-top: 0.2rem;
            white-space: nowrap;
            overflow: hidden;
            text-overflow: ellipsis;
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
            font-weight: 750 !important;
        }

        div[class*="st-key-status_actions_"] {
            gap: 0.32rem !important;
        }

        div[class*="st-key-status_actions_"] button {
            background: var(--tf-surface-2) !important;
            border: 1px solid var(--tf-border) !important;
            border-radius: 6px !important;
            box-shadow: none !important;
            color: var(--tf-muted) !important;
            font-size: 0.72rem !important;
            font-weight: 850 !important;
            letter-spacing: 0.01em;
            min-height: 2rem !important;
            padding: 0 0.42rem !important;
            transition: background 160ms ease, border-color 160ms ease, color 160ms ease;
            white-space: nowrap !important;
        }

        div[class*="st-key-status_actions_"] button:hover {
            background: var(--tf-pill-bg) !important;
            border-color: var(--tf-card-border) !important;
            color: var(--tf-text) !important;
        }

        div[class*="st-key-status_actions_"] button[kind="primary"] {
            background: var(--tf-accent) !important;
            border-color: var(--tf-accent) !important;
            color: var(--tf-button-active-text) !important;
        }

        div[class*="st-key-status_action_"] button:disabled,
        div[class*="st-key-status_action_"] button:disabled:hover {
            cursor: default !important;
            opacity: 1 !important;
        }

        div[class*="st-key-status_action_pending_"] button[kind="primary"] {
            background: var(--tf-status-pending-bg) !important;
            border-color: var(--tf-status-pending-border) !important;
            color: var(--tf-status-pending-text) !important;
        }

        div[class*="st-key-status_action_ok_"] button[kind="primary"] {
            background: var(--tf-status-ok-bg) !important;
            border-color: var(--tf-status-ok-border) !important;
            color: var(--tf-status-ok-text) !important;
        }

        div[class*="st-key-status_action_exists_"] button[kind="primary"] {
            background: var(--tf-status-exists-bg) !important;
            border-color: var(--tf-status-exists-border) !important;
            color: var(--tf-status-exists-text) !important;
        }

        div[class*="st-key-status_action_bad_"] button[kind="primary"] {
            background: var(--tf-status-bad-bg) !important;
            border-color: var(--tf-status-bad-border) !important;
            color: var(--tf-status-bad-text) !important;
        }

        [data-testid="stHorizontalBlock"]:has(.tf-domain-link)
        > [data-testid="stColumn"]:nth-child(6)
        button[data-testid="stPopoverButton"] {
            border-radius: 6px !important;
            min-height: 2.25rem !important;
            padding: 0 0.62rem !important;
            white-space: nowrap !important;
        }

        button[data-testid="stPopoverButton"] * {
            color: var(--tf-text) !important;
        }

        .st-key-mobile_navbar button[data-testid="stPopoverButton"] {
            border-radius: 999px !important;
            font-size: 1.2rem !important;
            min-height: 2.55rem !important;
            padding: 0 0.85rem 0 0.6rem !important;
            display: flex !important;
            align-items: center !important;
            justify-content: center !important;
            justify-self: center !important;
            align-self: center !important;
            margin: 0 auto !important;
            transform: translateY(6px) !important;
        }

        .st-key-mobile_navbar button[data-testid="stPopoverButton"] div[aria-hidden="true"],
        .st-key-mobile_navbar button[data-testid="stPopoverButton"] svg {
            display: none !important;
        }

        .tf-report-table-head {
            background: var(--tf-table-head);
            border: 1px solid var(--tf-card-border);
            border-radius: 8px;
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

        .tf-page-indicator {
            align-items: center;
            color: var(--tf-muted);
            display: flex;
            font-size: 0.88rem;
            font-weight: 760;
            height: 2.5rem;
            justify-content: center;
            white-space: nowrap;
        }

        .tf-page-size-note {
            color: var(--tf-muted);
            font-size: 0.78rem;
            font-weight: 760;
            padding-top: 0.55rem;
            text-align: right;
            white-space: nowrap;
        }

        .st-key-pagination_top_page_size,
        .st-key-pagination_bottom_page_size {
            margin-top: -1.35rem;
        }

        button[kind="primary"] {
            background: var(--tf-accent) !important;
            border-color: var(--tf-accent) !important;
            color: var(--tf-button-active-text) !important;
            font-weight: 850 !important;
        }

        @media (min-width: 761px) {
            .st-key-desktop_navbar {
                display: block !important;
            }

            .st-key-mobile_navbar {
                display: none !important;
            }

            .st-key-desktop_main_nav,
            .st-key-desktop_theme_switch {
                margin-top: 20px !important;
            }

            .st-key-top_navbar [data-testid="stColumn"]:has(.st-key-desktop_theme_switch) {
                align-items: center !important;
                display: flex !important;
                justify-content: flex-end !important;
            }
        }

        @media (max-width: 760px) {
            .st-key-desktop_navbar {
                display: none !important;
            }

            .st-key-mobile_navbar {
                display: block !important;
            }

            div[data-testid="stVerticalBlock"].st-key-top_navbar {
                padding: 0.3rem 1rem 1.4rem !important;
            }

        .st-key-mobile_navbar [data-testid="stHorizontalBlock"] {
            align-items: center !important;
            display: grid !important;
            grid-template-columns: minmax(0, 1fr) 3rem !important;
            gap: 0.7rem !important;
            width: 100% !important;
        }

            .st-key-mobile_navbar [data-testid="stColumn"] {
                min-width: 0 !important;
                width: 100% !important;
            }

            .st-key-mobile_navbar .tf-brand {
                gap: 0.65rem;
            }

            .st-key-mobile_navbar .tf-brand-logo,
            .st-key-mobile_navbar .tf-brand-mark {
                height: 2.25rem;
                width: 2.25rem;
            }

            .st-key-mobile_navbar .tf-brand-title {
                font-size: 1rem;
                overflow: hidden;
                text-overflow: ellipsis;
            }

            .st-key-mobile_navbar .tf-brand-subtitle {
                display: none;
            }

            .st-key-mobile_main_nav div[data-testid="stPills"] {
                justify-content: flex-start;
            }

            .st-key-mobile_theme_switch {
                justify-content: flex-start;
                margin-left: 0;
                margin-top: 0.7rem;
            }

            .st-key-mobile_theme_switch > div,
            .st-key-mobile_theme_switch label {
                justify-content: flex-start !important;
            }

            div[data-testid="stVerticalBlock"].st-key-page_content {
                padding: 1.25rem 1rem 2rem;
            }

            .tf-page-title {
                font-size: 1.6rem;
            }

            .tf-page-indicator {
                font-size: 0.8rem;
                justify-content: flex-start;
            }

            .tf-page-size-note {
                text-align: left;
            }

            .st-key-pagination_top_page_size,
            .st-key-pagination_bottom_page_size {
                margin-top: 0;
            }

            div[data-testid="stExpander"]:has(.tf-filters-anchor) .st-key-filter_show_reviewed {
                padding-bottom: 0;
            }

            .tf-table-head-wrapper {
                overflow-x: visible;
            }

            .tf-table-head-desktop {
                display: none !important;
            }

            .tf-table-head-mobile {
                display: grid !important;
                grid-template-columns: 1fr auto auto;
                min-width: 0;
                width: 100% !important;
            }

            [data-testid="stVerticalBlock"]:has(
                > [data-testid="stLayoutWrapper"] > [data-testid="stHorizontalBlock"] .tf-domain-link
            ) {
                max-width: 100% !important;
                overflow-x: visible !important;
                width: 100% !important;
            }

            [data-testid="stVerticalBlock"]:has(
                > [data-testid="stLayoutWrapper"] > [data-testid="stHorizontalBlock"] .tf-domain-link
            ) [data-testid="stLayoutWrapper"],
            [data-testid="stVerticalBlock"]:has(
                > [data-testid="stLayoutWrapper"] > [data-testid="stHorizontalBlock"] .tf-domain-link
            ) [data-testid="stElementContainer"],
            [data-testid="stVerticalBlock"]:has(
                > [data-testid="stLayoutWrapper"] > [data-testid="stHorizontalBlock"] .tf-domain-link
            ) .stMarkdown,
            [data-testid="stVerticalBlock"]:has(
                > [data-testid="stLayoutWrapper"] > [data-testid="stHorizontalBlock"] .tf-domain-link
            ) .stMarkdown > div {
                max-width: 100% !important;
                min-width: 0 !important;
                width: 100% !important;
            }

            [data-testid="stHorizontalBlock"]:has(.tf-domain-link) {
                align-items: stretch !important;
                display: grid !important;
                gap: 0.8rem !important;
                grid-template-columns: minmax(0, 1fr) !important;
                max-width: 100% !important;
                min-width: 0 !important;
                width: 100% !important;
            }

            [data-testid="stHorizontalBlock"]:has(.tf-domain-link) .stCheckbox label {
                font-size: 0.82rem !important;
                min-height: 1.5rem;
            }

            [data-testid="stHorizontalBlock"]:has(.tf-domain-link) > [data-testid="stColumn"] {
                max-width: 100% !important;
                min-width: 0 !important;
                width: 100% !important;
            }

            [data-testid="stHorizontalBlock"]:has(.tf-domain-link) > [data-testid="stColumn"]:nth-child(2) {
                display: none !important;
            }

            [data-testid="stHorizontalBlock"]:has(.tf-domain-link) > [data-testid="stColumn"]:nth-child(3) {
                display: none !important;
            }

            [data-testid="stVerticalBlock"]:has(
                > [data-testid="stLayoutWrapper"] > [data-testid="stHorizontalBlock"] .tf-domain-link
            )
            div[data-testid="stExpander"] {
                max-width: 100% !important;
                min-width: 0 !important;
                width: 100% !important;
            }

            .tf-mobile-field-label {
                color: var(--tf-muted);
                display: block !important;
                font-size: 0.72rem;
                font-weight: 850;
                letter-spacing: 0.04em;
                margin-bottom: 0.28rem;
                text-transform: uppercase;
            }

            .stElementContainer:has(.tf-mobile-widget-label) {
                display: block !important;
            }

            .tf-domain-cell,
            .tf-summary {
                overflow-wrap: anywhere;
                width: 100%;
            }

            .tf-domain-primary {
                align-items: flex-start;
                display: flex;
                gap: 0.75rem;
                justify-content: space-between;
                width: 100%;
            }

            .tf-domain-primary .tf-domain-link {
                min-width: 0;
            }

            .tf-domain-url-mobile {
                color: var(--tf-muted);
                display: block;
                font-size: 0.78rem;
                font-weight: 650;
                line-height: 1.35;
                margin-top: 0.26rem;
                overflow-wrap: anywhere;
            }

            .tf-summary-mobile {
                display: block;
                margin-top: 0.62rem;
            }

            .tf-domain-pills {
                display: none !important;
            }

            .tf-score-mobile {
                display: flex;
                flex: 0 0 auto;
                justify-content: flex-end;
            }

            .tf-score-mobile .tf-score {
                font-size: 0.82rem;
                min-width: 2.75rem;
                padding: 0.34rem 0.55rem;
            }

            .tf-report-table-head {
                display: none;
            }

            .tf-metric-card {
                min-height: 0;
            }

            .tf-metric-topline {
                align-items: flex-start;
                gap: 0.45rem;
            }

            .tf-opportunity-kpis {
                grid-template-columns: repeat(2, minmax(0, 1fr));
            }

            .tf-notes-panel {
                gap: 0.5rem;
            }

            .tf-notes-header {
                gap: 0.5rem;
                margin-bottom: 0.4rem;
                padding-bottom: 0.4rem;
            }

            .tf-notes-title {
                font-size: 0.82rem;
            }

            .tf-notes-subtitle {
                font-size: 0.68rem;
                max-width: 160px;
            }

            .tf-notes-list {
                max-height: 12rem;
                gap: 0.35rem;
            }

            .tf-note {
                padding: 0.42rem 0.5rem;
                gap: 0.22rem;
                border-radius: 6px;
            }

            .tf-note-meta strong {
                font-size: 0.72rem;
            }

            .tf-note-meta span {
                font-size: 0.62rem;
            }

            .tf-note p {
                font-size: 0.76rem;
                line-height: 1.38;
            }

            .tf-note-empty {
                font-size: 0.74rem;
                padding: 0.5rem 0.6rem;
            }

            .tf-note-composer-row {
                grid-template-columns: 1fr;
            }

            .tf-note-composer-title {
                font-size: 0.7rem;
            }

            div[data-testid="stPopover"] {
                max-width: 92vw !important;
                min-width: 0 !important;
            }

            div[data-testid="stPopover"] > div {
                padding: 0.6rem 0.7rem !important;
            }

            div[data-testid="stPopover"] .tf-note-composer [data-testid="stTextInput"] input,
            div[data-testid="stPopover"] .tf-note-composer [data-testid="stTextArea"] textarea {
                font-size: 0.8rem !important;
                padding: 0.4rem 0.5rem !important;
            }
        }
        </style>
        """.replace("__THEME_VARS__", _theme_vars(theme_name)),
        unsafe_allow_html=True,
    )


def ensure_ui_state() -> None:
    query_theme = _theme_from_query_params()
    nav_keys = ("desktop_main_nav", "mobile_main_nav")
    theme_keys = ("desktop_theme_switch", "mobile_theme_switch")

    if "active_tab" not in st.session_state:
        st.session_state.active_tab = NAV_ITEMS[0]
    elif st.session_state.active_tab not in NAV_ITEMS:
        st.session_state.active_tab = NAV_ITEMS[0]

    for key in nav_keys:
        selected = st.session_state.get(key)
        previous = st.session_state.get(f"_{key}_last", selected)
        if selected in NAV_ITEMS and selected != previous:
            st.session_state.active_tab = selected
            break

    for key in nav_keys:
        st.session_state[key] = st.session_state.active_tab
        st.session_state[f"_{key}_last"] = st.session_state.active_tab

    query_theme_changed = False
    if "theme_switch" not in st.session_state:
        st.session_state.theme_switch = query_theme != "Light"
        st.session_state.theme_query_applied = query_theme
        query_theme_changed = True
    elif query_theme and st.session_state.get("theme_query_applied") != query_theme:
        st.session_state.theme_switch = query_theme == "Dark"
        st.session_state.theme_query_applied = query_theme
        query_theme_changed = True

    if not query_theme_changed:
        for key in theme_keys:
            selected = bool(st.session_state.get(key, st.session_state.theme_switch))
            previous = bool(st.session_state.get(f"_{key}_last", selected))
            if selected != previous:
                st.session_state.theme_switch = selected
                break

    st.session_state.theme_mode = "Dark" if st.session_state.theme_switch else "Light"

    for key in theme_keys:
        st.session_state[key] = st.session_state.theme_switch
        st.session_state[f"_{key}_last"] = st.session_state.theme_switch


def _logo_data_uri() -> str | None:
    logo_path = Path(__file__).resolve().parent.parent / "assets" / "logo.png"
    if not logo_path.exists():
        return None

    encoded = base64.b64encode(logo_path.read_bytes()).decode("ascii")
    return f"data:image/png;base64,{encoded}"


def _brand_html(*, compact: bool = False) -> str:
    logo_uri = _logo_data_uri()
    logo_html = (
        f'<img class="tf-brand-logo" src="{logo_uri}" alt="TrendingFounder logo" />'
        if logo_uri
        else '<div class="tf-brand-mark">TF</div>'
    )
    compact_class = " tf-brand-compact" if compact else ""
    subtitle = "" if compact else '<div class="tf-brand-subtitle">Domain Discovery Dashboard</div>'
    return (
        f'<div class="tf-brand{compact_class}">'
        f"{logo_html}"
        "<div>"
        '<div class="tf-brand-title">TrendingFounder</div>'
        f"{subtitle}"
        "</div>"
        "</div>"
    )


def _sync_nav_from_widgets() -> None:
    for key in ("desktop_main_nav", "mobile_main_nav"):
        selected = st.session_state.get(key)
        previous = st.session_state.get(f"_{key}_last", selected)
        if selected in NAV_ITEMS and selected != previous:
            st.session_state.active_tab = selected
            break

    for key in ("desktop_main_nav", "mobile_main_nav"):
        selected = st.session_state.get(key)
        st.session_state[f"_{key}_last"] = selected if selected in NAV_ITEMS else st.session_state.active_tab


def _sync_theme_from_widgets() -> None:
    for key in ("desktop_theme_switch", "mobile_theme_switch"):
        selected = bool(st.session_state.get(key))
        previous = bool(st.session_state.get(f"_{key}_last", selected))
        if selected != previous:
            st.session_state.theme_switch = selected
            break

    st.session_state.theme_mode = "Dark" if st.session_state.theme_switch else "Light"
    for key in ("desktop_theme_switch", "mobile_theme_switch"):
        st.session_state[f"_{key}_last"] = bool(st.session_state.get(key))


def render_navbar() -> str:
    ensure_ui_state()

    with st.container(key="desktop_navbar"):
        brand_col, nav_col, theme_col = st.columns([1.05, 1, 1.05], vertical_alignment="center")
        brand_col.markdown(_brand_html(), unsafe_allow_html=True)
        nav_col.pills(
            "Navigation",
            NAV_ITEMS,
            key="desktop_main_nav",
            label_visibility="collapsed",
        )
        theme_col.toggle("Dark mode", key="desktop_theme_switch")

    with st.container(key="mobile_navbar"):
        brand_col, menu_col = st.columns([1, 0.16], vertical_alignment="center")
        brand_col.markdown(_brand_html(compact=True), unsafe_allow_html=True)
        with menu_col:
            with st.popover("☰", width="stretch"):
                st.pills(
                    "Navigation",
                    NAV_ITEMS,
                    key="mobile_main_nav",
                    label_visibility="collapsed",
                )
                st.toggle("Dark mode", key="mobile_theme_switch")

    _sync_nav_from_widgets()
    _sync_theme_from_widgets()
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
    st.session_state.setdefault("_pending_domain_status_updates", {})[domain_id] = new_status
    st.session_state["_collected_optimistic_refresh"] = True
    _STATUS_UPDATE_EXECUTOR.submit(_persist_domain_status_change, domain_id, new_status)


def _persist_domain_status_change(domain_id: str, new_status: str) -> None:
    repo = DomainRepository()
    repo.update_review_status(domain_id, ReviewStatus(new_status))
    clear_dashboard_caches()


def on_add_comment(domain_id: str, author: str, message: str) -> None:
    repo = CommentRepository()
    repo.add_comment(domain_id, author, message)
    clear_dashboard_caches()
    st.rerun()


def _session_option(key: str, options: list[str], default: str) -> str:
    value = st.session_state.get(key, default)
    return value if value in options else default


def _status_filter_from_session() -> str:
    status_values = {
        status: bool(st.session_state.get(f"filter_status_{status}", True))
        for status in STATUS_FILTER_OPTIONS
        if status != "All Statuses"
    }
    selected = [status for status, checked in status_values.items() if checked]
    if not selected:
        return "__none__"
    if len(selected) == len(status_values):
        return "All Statuses"
    return ",".join(selected)


def _date_range_from_session() -> tuple[date, date]:
    value = st.session_state.get("filter_date_range")
    if isinstance(value, date):
        return value, value
    if isinstance(value, tuple | list):
        if not value:
            return _default_date_range()
        default_start, default_end = _default_date_range()
        start = value[0] or default_start
        end = value[1] if len(value) > 1 and value[1] else start
        return (end, start) if start > end else (start, end)
    return _default_date_range()


def _session_page_size() -> int:
    try:
        value = int(st.session_state.get("collected_page_size", DEFAULT_PAGE_SIZE))
    except (TypeError, ValueError):
        value = DEFAULT_PAGE_SIZE
    if value not in PAGE_SIZE_OPTIONS:
        value = DEFAULT_PAGE_SIZE
    st.session_state.collected_page_size = value
    return value


def _filter_signature(filters: dict, page_size: int) -> tuple:
    return (
        filters["date_start"].isoformat(),
        filters["date_end"].isoformat(),
        filters["status_filter"],
        filters["category_filter"],
        filters["show_reviewed"],
        filters["sort_by"],
        page_size,
        filters["min_opportunity_score"],
        filters["min_opportunity_confidence"],
        filters["hide_global_giants"],
        filters["opportunity_type_filter"],
    )


def _render_signature(filters: dict, page: int, page_size: int) -> tuple:
    return _filter_signature(filters, page_size) + (page,)


def _apply_pending_review_status_updates(df, pending_updates: dict, show_reviewed: bool):
    if df is None or df.empty or not pending_updates or "id" not in df.columns:
        return df

    df = df.copy()
    row_ids = df["id"].astype(str)
    pending_by_id = {str(domain_id): status for domain_id, status in pending_updates.items()}
    if "Status" in df.columns:
        df.loc[row_ids.isin(pending_by_id), "Status"] = row_ids.map(pending_by_id)
    if show_reviewed:
        return df
    return df[df["Status"].fillna("pending") == "pending"]


def _prune_confirmed_review_status_updates(df, pending_updates: dict) -> None:
    if df is None or df.empty or not pending_updates or "id" not in df.columns or "Status" not in df.columns:
        return

    confirmed = {
        str(row["id"])
        for _, row in df.iterrows()
        if pending_updates.get(str(row["id"])) == row["Status"]
    }
    for domain_id in confirmed:
        pending_updates.pop(domain_id, None)


def _sync_collected_pagination(filters: dict) -> tuple[int, int]:
    page_size = _session_page_size()
    signature = _filter_signature(filters, page_size)
    if st.session_state.get("_collected_filter_signature") != signature:
        st.session_state.collected_page = 1
        st.session_state._collected_filter_signature = signature

    try:
        page = int(st.session_state.get("collected_page", 1))
    except (TypeError, ValueError):
        page = 1
    page = max(1, page)
    st.session_state.collected_page = page
    return page, page_size


def _load_collected_data_for_render(filters: dict, page: int, page_size: int):
    signature = _render_signature(filters, page, page_size)
    optimistic_refresh = bool(st.session_state.get("_collected_optimistic_refresh", False))
    snapshot = st.session_state.get("_collected_data_snapshot")
    if optimistic_refresh and isinstance(snapshot, dict) and snapshot.get("signature") == signature:
        st.session_state["_collected_optimistic_refresh"] = False
        return snapshot["df"], snapshot["total_count"], True

    df, total_count = _load_collected_data_page(filters, page, page_size)
    st.session_state["_collected_data_snapshot"] = {"signature": signature, "df": df, "total_count": total_count}
    return df, total_count, False


def _load_collected_data_page(filters: dict, page: int, page_size: int):
    df, total_count = load_collected_data(
        show_reviewed=filters["show_reviewed"],
        sort_by=filters["sort_by"],
        search_query=filters["search_query"],
        status_filter=filters["status_filter"],
        category_filter=filters["category_filter"],
        date_start=filters["date_start"],
        date_end=filters["date_end"],
        page=page,
        page_size=page_size,
        min_opportunity_score=filters["min_opportunity_score"],
        min_opportunity_confidence=filters["min_opportunity_confidence"],
        opportunity_type_filter=filters["opportunity_type_filter"],
        hide_global_giants=filters["hide_global_giants"],
    )
    return df, total_count


def _clear_collected_data_loader_cache() -> None:
    clear_cache = getattr(load_collected_data, "clear", None)
    if callable(clear_cache):
        clear_cache()


def _refill_page_limit(page: int, page_size: int, total_count: int, pending_updates: dict) -> int:
    total_pages = max(page + 1, ceil(max(total_count, page_size) / page_size))
    pending_pages = max(1, ceil(len(pending_updates) / page_size))
    return min(total_pages, page + pending_pages)


def _combine_collected_frames(frames: list, page_size: int):
    if not frames:
        return pd.DataFrame()

    combined = pd.concat(frames, ignore_index=True)
    if "id" in combined.columns:
        combined = combined.drop_duplicates(subset=["id"], keep="first")
    return combined.head(page_size)


def _load_collected_data_refill_batch(
    filters: dict,
    page: int,
    page_size: int,
    total_count: int,
    pending_updates: dict,
):
    _clear_collected_data_loader_cache()
    latest_total_count = total_count
    visible_frames = []
    last_page = _refill_page_limit(page, page_size, total_count, pending_updates)

    for refill_page in range(page, last_page + 1):
        candidate_df, candidate_total_count = _load_collected_data_page(filters, refill_page, page_size)
        if candidate_total_count:
            latest_total_count = candidate_total_count
        if candidate_df is None or candidate_df.empty:
            continue

        _prune_confirmed_review_status_updates(candidate_df, pending_updates)
        candidate_visible_df = _apply_pending_review_status_updates(
            candidate_df,
            pending_updates,
            show_reviewed=False,
        )
        if candidate_visible_df is None or candidate_visible_df.empty:
            continue

        visible_frames.append(candidate_visible_df)
        combined_df = _combine_collected_frames(visible_frames, page_size)
        if len(combined_df) >= page_size:
            return combined_df, latest_total_count

    return _combine_collected_frames(visible_frames, page_size), latest_total_count


def _maybe_refill_collected_data_after_optimistic_clear(
    filters: dict,
    page: int,
    page_size: int,
    visible_df,
    source_df,
    total_count: int,
    pending_updates: dict,
    render_signature: tuple,
):
    if (
        filters["show_reviewed"]
        or not pending_updates
        or source_df is None
        or source_df.empty
        or visible_df is None
        or not visible_df.empty
    ):
        return visible_df, total_count, False

    refill_df, refill_total_count = _load_collected_data_refill_batch(
        filters,
        page,
        page_size,
        total_count,
        pending_updates,
    )
    if refill_df.empty:
        return visible_df, total_count, False

    st.session_state["_collected_data_snapshot"] = {
        "signature": render_signature,
        "df": refill_df,
        "total_count": refill_total_count,
    }
    return refill_df, refill_total_count, True


def _load_comments_for_render(df, signature: tuple, use_snapshot: bool):
    snapshot = st.session_state.get("_collected_comments_snapshot")
    if use_snapshot and isinstance(snapshot, dict) and snapshot.get("signature") == signature:
        return snapshot["comments_data"]

    comments_data = load_comments(df["id"].tolist()) if df is not None and not df.empty and "id" in df.columns else {}
    st.session_state["_collected_comments_snapshot"] = {
        "signature": signature,
        "comments_data": comments_data,
    }
    return comments_data


def current_filter_values() -> dict:
    """Read filter widget state before rendering widgets to avoid header reflow."""
    date_start, date_end = _date_range_from_session()
    return {
        "search_query": "",
        "status_filter": _status_filter_from_session(),
        "category_filter": _session_option("filter_category", CATEGORY_FILTER_OPTIONS, CATEGORY_FILTER_OPTIONS[0]),
        "show_reviewed": bool(st.session_state.get("filter_show_reviewed", False)),
        "sort_by": _session_option("filter_sort", SORT_OPTIONS, SORT_OPTIONS[0]),
        "min_score": 0,
        "date_start": date_start,
        "date_end": date_end,
        "min_opportunity_score": int(st.session_state.get("filter_min_opp_score", 0)),
        "min_opportunity_confidence": int(st.session_state.get("filter_min_opp_confidence", 0)),
        "hide_global_giants": bool(st.session_state.get("filter_hide_giants", False)),
        "opportunity_type_filter": _session_option(
            "filter_opp_type",
            OPPORTUNITY_TYPE_OPTIONS,
            OPPORTUNITY_TYPE_OPTIONS[0],
        ),
    }


def _date_range_label(date_start: date, date_end: date) -> str:
    if date_start == date_end == date.today():
        return "Best score today across the world"
    if date_start == date_end:
        return f"Best score on {date_start.isoformat()}"
    return f"Best score from {date_start.isoformat()} to {date_end.isoformat()}"


def render_pagination_controls(
    total_count: int,
    page: int,
    page_size: int,
    key_prefix: str,
    show_page_size: bool = True,
) -> None:
    total_pages = max(1, ceil(total_count / page_size)) if page_size else 1
    page = min(max(1, page), total_pages)

    prev_col, info_col, next_col, size_col = st.columns([0.8, 1.4, 0.8, 1.0], vertical_alignment="center")
    if prev_col.button("Previous", key=f"{key_prefix}_prev", disabled=page <= 1, width="stretch"):
        st.session_state.collected_page = max(1, page - 1)
        st.rerun()

    info_col.markdown(
        f"<div class='tf-page-indicator'>Page {page} / {total_pages} · {total_count} total</div>",
        unsafe_allow_html=True,
    )

    if next_col.button("Next", key=f"{key_prefix}_next", disabled=page >= total_pages, width="stretch"):
        st.session_state.collected_page = min(total_pages, page + 1)
        st.rerun()

    if show_page_size:
        selected_size = size_col.selectbox(
            "Page size",
            PAGE_SIZE_OPTIONS,
            index=PAGE_SIZE_OPTIONS.index(page_size),
            key=f"{key_prefix}_page_size",
        )
        if selected_size != page_size:
            st.session_state.collected_page_size = selected_size
            st.session_state.collected_page = 1
            st.rerun()
    else:
        size_col.markdown(
            f"<div class='tf-page-size-note'>{page_size} rows / page</div>",
            unsafe_allow_html=True,
        )


def render_collected_data_page() -> None:
    filters = current_filter_values()
    page, page_size = _sync_collected_pagination(filters)

    render_signature = _render_signature(filters, page, page_size)
    df, total_count, used_data_snapshot = _load_collected_data_for_render(filters, page, page_size)
    if df.empty and page > 1:
        st.session_state.collected_page = 1
        st.rerun()
    pending_status_updates = st.session_state.get("_pending_domain_status_updates", {})
    _prune_confirmed_review_status_updates(df, pending_status_updates)
    source_df = df
    df = _apply_pending_review_status_updates(
        df,
        pending_status_updates,
        filters["show_reviewed"],
    )
    df, total_count, refilled_after_clear = _maybe_refill_collected_data_after_optimistic_clear(
        filters=filters,
        page=page,
        page_size=page_size,
        visible_df=df,
        source_df=source_df,
        total_count=total_count,
        pending_updates=pending_status_updates,
        render_signature=render_signature,
    )
    used_data_snapshot = used_data_snapshot and not refilled_after_clear

    render_page_header(
        "Collected Data",
        f"{total_count} domains found · {_date_range_label(filters['date_start'], filters['date_end'])}",
    )
    render_filters(show_reviewed_default=filters["show_reviewed"], expanded=False)

    comments_data = _load_comments_for_render(df, render_signature, used_data_snapshot)
    render_domain_table(
        df,
        on_status_change=on_status_change,
        on_add_comment=on_add_comment,
        comments_data=comments_data,
    )
    render_pagination_controls(total_count, page, page_size, "pagination_bottom", show_page_size=True)


def _github_review_status_options() -> list[str]:
    return [status.value for status in GitHubRepoReviewStatus]


def _render_github_stats(stats: dict) -> None:
    latest_run = stats.get("latest_run") or {}
    cards = [
        ("New Today", stats.get("new_today", 0), "First seen today"),
        ("Tracked Repos", stats.get("total_tracked", 0), "Total repos"),
        ("Snapshots", stats.get("snapshot_count", 0), "Total runs"),
        ("New This Week", stats.get("new_this_week", 0), "First seen in 7 days"),
        ("Latest Status", latest_run.get("status", "N/A"), "GitHub topic crawl"),
        (
            "Latest Fetch",
            f"{latest_run.get('fetched_count', 0)} / {latest_run.get('new_count', 0)}",
            "Fetched / new",
        ),
    ]

    cols = st.columns(len(cards), gap="medium")
    for col, (label, value, detail) in zip(cols, cards):
        col.markdown(
            (
                "<div class='tf-metric-card'>"
                "<div class='tf-metric-topline'>"
                f"<div class='tf-metric-label'>{escape(str(label))}</div>"
                f"<div class='tf-metric-value'>{escape(str(value))}</div>"
                "</div>"
                f"<div class='tf-metric-detail'>{escape(str(detail))}</div>"
                "</div>"
            ),
            unsafe_allow_html=True,
        )


def _github_filter_values() -> dict:
    languages = load_github_language_options()
    with st.container(border=True):
        cols = st.columns([1.1, 1.1, 0.8, 1, 1, 1.4], gap="medium")
        language = cols[0].selectbox("Language", languages, key="github_language_filter")
        status = cols[1].selectbox(
            "Review status",
            ["All Statuses", *_github_review_status_options()],
            key="github_status_filter",
        )
        min_stars = cols[2].number_input("Min stars", min_value=0, step=100, key="github_min_stars")
        first_seen_start = cols[3].date_input("First seen from", value=None, key="github_first_seen_start")
        first_seen_end = cols[4].date_input("First seen to", value=None, key="github_first_seen_end")
        search_query = cols[5].text_input("Search", placeholder="repo or description", key="github_search")

    return {
        "language_filter": language,
        "review_status_filter": status,
        "min_stars": int(min_stars),
        "first_seen_start": first_seen_start,
        "first_seen_end": first_seen_end,
        "search_query": search_query,
    }


def _apply_github_table_edits(original_df, edited_df) -> int:
    updates = 0
    review_options = set(_github_review_status_options())

    for repo_id, row in edited_df.iterrows():
        original = original_df.loc[repo_id]
        if bool(row.get("mark_seen")):
            mark_github_repo_seen(str(repo_id))
            updates += 1
            continue

        status = str(row.get("review_status") or "pending")
        if status in review_options and status != str(original.get("review_status")):
            update_github_repo_review_status(str(repo_id), status)
            updates += 1

        notes = str(row.get("notes") or "")
        if notes != str(original.get("notes") or ""):
            update_github_repo_notes(str(repo_id), notes)
            updates += 1

    return updates


def _github_editor_columns() -> list[str]:
    return [
        "mark_seen",
        "full_name",
        "html_url",
        "description",
        "language",
        "stargazers_count",
        "forks_count",
        "open_issues_count",
        "created_at",
        "pushed_at",
        "first_seen_at",
        "review_status",
        "notes",
    ]


def _apply_github_editor_state_seen_edits(editor_state: dict, repo_ids: list[str]) -> int:
    updates = 0
    edited_rows = editor_state.get("edited_rows", {}) if isinstance(editor_state, dict) else {}
    for row_position, row_edits in edited_rows.items():
        if not isinstance(row_edits, dict) or not bool(row_edits.get("mark_seen")):
            continue
        try:
            repo_id = repo_ids[int(row_position)]
        except (IndexError, TypeError, ValueError):
            continue
        mark_github_repo_seen(str(repo_id))
        updates += 1
    return updates


def _on_github_editor_change(repo_ids: list[str]) -> None:
    updates = _apply_github_editor_state_seen_edits(st.session_state.get("github_opencode_editor", {}), repo_ids)
    if updates:
        st.toast(f"Marked {updates} GitHub repo{'s' if updates != 1 else ''} as seen.")


def render_github_opencode_page() -> None:
    stats = load_github_crawl_stats()
    render_page_header("GitHub Opencode", "New repositories entering the top topic snapshot by stars")
    _render_github_stats(stats)

    filters = _github_filter_values()
    df = load_new_github_repositories(**filters)

    st.markdown("<div class='tf-section-title'>New repositories</div>", unsafe_allow_html=True)
    if df.empty:
        st.markdown(
            """
            <div class="tf-empty-state">
                <div class="tf-empty-state-title">No new GitHub repositories in this view</div>
                <div class="tf-empty-state-text">
                    The first crawl is baseline-only. Later crawls show repositories that were not seen before.
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )
        return

    action_cols = st.columns([1, 4], gap="medium")
    with action_cols[0]:
        if st.button("Mark all as seen", type="secondary", width="stretch"):
            updated = mark_github_repos_seen(df["id"].dropna().astype(str).tolist())
            st.toast(f"Marked {updated} GitHub repo{'s' if updated != 1 else ''} as seen.")
            st.rerun()

    columns = _github_editor_columns()
    editor_df = df.set_index("id")[[column for column in columns if column in df.columns]]
    repo_ids = editor_df.index.astype(str).tolist()
    edited_df = st.data_editor(
        editor_df,
        width="stretch",
        hide_index=True,
        disabled=[
            "full_name",
            "html_url",
            "description",
            "language",
            "stargazers_count",
            "forks_count",
            "open_issues_count",
            "created_at",
            "pushed_at",
            "first_seen_at",
        ],
        column_config={
            "full_name": st.column_config.TextColumn("Repository", width="medium"),
            "html_url": st.column_config.LinkColumn("URL", display_text="Open", width="small"),
            "description": st.column_config.TextColumn("Description", width="large"),
            "language": st.column_config.TextColumn("Language", width="small"),
            "stargazers_count": st.column_config.NumberColumn("Stars", format="%d", width="small"),
            "forks_count": st.column_config.NumberColumn("Forks", format="%d", width="small"),
            "open_issues_count": st.column_config.NumberColumn("Issues", format="%d", width="small"),
            "created_at": st.column_config.TextColumn("Created", width="medium"),
            "pushed_at": st.column_config.TextColumn("Pushed", width="medium"),
            "first_seen_at": st.column_config.TextColumn("First seen", width="medium"),
            "review_status": st.column_config.SelectboxColumn(
                "Status",
                options=_github_review_status_options(),
                required=True,
                width="small",
            ),
            "notes": st.column_config.TextColumn("Notes", width="medium"),
            "mark_seen": st.column_config.CheckboxColumn("Seen", help="Mark as seen and ignore", width="small"),
        },
        key="github_opencode_editor",
        on_change=_on_github_editor_change,
        args=(repo_ids,),
    )

    updates = _apply_github_table_edits(editor_df, edited_df)
    if updates:
        st.toast(f"Updated {updates} GitHub repo row{'s' if updates != 1 else ''}.")
        st.rerun()


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


def _country_display_name(country_code, country_name="") -> str:
    if not _is_missing(country_name):
        return str(country_name)
    code = _display_value(country_code, "")
    return COUNTRY_CODES.get(code.upper(), code) if code else "N/A"


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
        country_label = _country_display_name(row.get("country_code"), row.get("country_name"))

        with st.container(border=True):
            cols = st.columns([1.2, 1, 0.8, 0.9, 0.9, 2], gap="medium", vertical_alignment="center")
            cols[0].markdown(f"**{escape(str(country_label))}**")
            cols[1].markdown(_status_pill(_display_value(row.get("country_status"), "pending")), unsafe_allow_html=True)
            cols[2].write(_int_value(row.get("items_found")))
            cols[3].write(_int_value(row.get("new_domains")))
            cols[4].write(_int_value(row.get("duplicate_domains")))
            error_message = "" if _is_missing(row.get("error_message")) else str(row.get("error_message"))
            cols[5].markdown(f"<span class='tf-muted'>{escape(error_message or 'None')}</span>", unsafe_allow_html=True)


def _format_run_time(value: str | None) -> str:
    if not value:
        return "—"
    try:
        from datetime import datetime
        return datetime.fromisoformat(value.replace("Z", "+00:00")).strftime("%Y-%m-%d %H:%M UTC")
    except Exception:
        return value


def _run_status_label(run: dict) -> str:
    status = (run.get("status") or "").lower()
    conclusion = (run.get("conclusion") or "").lower()
    if status == "completed":
        return conclusion or "completed"
    return status or "unknown"


def render_run_crawl_panel() -> None:
    st.markdown("<div class='tf-section-title'>Run Crawl</div>", unsafe_allow_html=True)
    with st.container(border=True):
        col_form, col_runs = st.columns([1, 1.4], gap="large")

        with col_form:
            with st.form("run_crawl_form", clear_on_submit=False):
                skip_domain = st.checkbox("Skip domain crawler", value=False)
                skip_github = st.checkbox("Skip GitHub opencode crawl", value=False)
                skip_score = st.checkbox(
                    "Skip opportunity scoring",
                    value=False,
                    help="Only affects the domain crawl step.",
                )
                submitted = st.form_submit_button("▶ Trigger crawl workflow", type="primary")
            if submitted:
                try:
                    trigger_workflow(
                        skip_domain=skip_domain,
                        skip_github=skip_github,
                        skip_score=skip_score,
                    )
                    st.success("Workflow dispatched. Refresh in a few seconds to see the new run.")
                except GitHubActionsError as exc:
                    st.error(str(exc))

        with col_runs:
            st.markdown("**Recent runs**")
            try:
                runs = list_recent_runs(limit=5)
            except GitHubActionsError as exc:
                st.info(str(exc))
                return

            if not runs:
                st.caption("No runs yet.")
                return

            for run in runs:
                label = _run_status_label(run)
                started = _format_run_time(run.get("run_started_at") or run.get("created_at"))
                url = run.get("html_url") or "#"
                st.markdown(
                    f"- [{label}]({url}) · {escape(run.get('event') or '')} · {escape(started)}"
                )


def render_reports_page() -> None:
    stats = load_stats()
    country_df = load_country_progress()
    render_page_header("Reports", "Crawl metrics, enrichment progress, and country-by-country status")

    render_run_crawl_panel()

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
    st.html(
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
        unsafe_allow_javascript=True,
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
        elif active_tab == "GitHub Opencode":
            render_github_opencode_page()
        else:
            render_collected_data_page()


if __name__ == "__main__":
    render()
