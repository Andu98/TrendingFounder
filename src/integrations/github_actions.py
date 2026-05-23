"""Trigger and inspect the GitHub Actions `Crawl` workflow.

Reads credentials from environment variables first, then `st.secrets`
when running inside Streamlit. Required keys:

- ``GH_REPO``           — owner/repo (e.g. ``tudoralexandru/TrendingFounder``)
- ``GH_DISPATCH_TOKEN`` — fine-grained PAT with ``Actions: read/write``
- ``GH_WORKFLOW_FILE``  — workflow filename (default: ``crawl.yml``)
- ``GH_WORKFLOW_REF``   — git ref to run on (default: ``main``)
"""
from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Any

import httpx

_API_BASE = "https://api.github.com"
_DEFAULT_WORKFLOW = "crawl.yml"
_DEFAULT_REF = "main"


class GitHubActionsError(RuntimeError):
    """Raised when the GitHub Actions API call fails or config is missing."""


def _read_secret(name: str) -> str | None:
    value = os.getenv(name)
    if value:
        return value
    try:
        import streamlit as st  # local import; not required outside Streamlit
    except ImportError:
        return None
    try:
        return st.secrets[name]  # type: ignore[index]
    except (KeyError, FileNotFoundError, AttributeError):
        return None


@dataclass(frozen=True)
class WorkflowConfig:
    repo: str
    token: str
    workflow: str = _DEFAULT_WORKFLOW
    ref: str = _DEFAULT_REF

    @property
    def runs_url(self) -> str:
        return f"{_API_BASE}/repos/{self.repo}/actions/workflows/{self.workflow}/runs"

    @property
    def dispatch_url(self) -> str:
        return f"{_API_BASE}/repos/{self.repo}/actions/workflows/{self.workflow}/dispatches"


def load_config() -> WorkflowConfig:
    repo = _read_secret("GH_REPO")
    token = _read_secret("GH_DISPATCH_TOKEN")
    missing = [name for name, val in (("GH_REPO", repo), ("GH_DISPATCH_TOKEN", token)) if not val]
    if missing:
        raise GitHubActionsError(
            "Missing GitHub Actions config: " + ", ".join(missing)
            + ". Set env vars, Streamlit Community Cloud secrets, or local .streamlit/secrets.toml."
        )
    return WorkflowConfig(
        repo=repo,  # type: ignore[arg-type]
        token=token,  # type: ignore[arg-type]
        workflow=_read_secret("GH_WORKFLOW_FILE") or _DEFAULT_WORKFLOW,
        ref=_read_secret("GH_WORKFLOW_REF") or _DEFAULT_REF,
    )


def _headers(cfg: WorkflowConfig) -> dict[str, str]:
    return {
        "Accept": "application/vnd.github+json",
        "Authorization": f"Bearer {cfg.token}",
        "X-GitHub-Api-Version": "2022-11-28",
    }


def trigger_workflow(
    *,
    skip_domain: bool = False,
    skip_github: bool = False,
    skip_score: bool = False,
    cfg: WorkflowConfig | None = None,
) -> None:
    """Dispatch the Crawl workflow with the given input flags."""
    cfg = cfg or load_config()
    payload: dict[str, Any] = {
        "ref": cfg.ref,
        "inputs": {
            "skip_domain": str(bool(skip_domain)).lower(),
            "skip_github": str(bool(skip_github)).lower(),
            "skip_score": str(bool(skip_score)).lower(),
        },
    }
    with httpx.Client(timeout=15.0) as client:
        response = client.post(cfg.dispatch_url, headers=_headers(cfg), json=payload)
    if response.status_code != 204:
        raise GitHubActionsError(
            f"workflow_dispatch failed: HTTP {response.status_code} {response.text}"
        )


def list_recent_runs(limit: int = 5, cfg: WorkflowConfig | None = None) -> list[dict[str, Any]]:
    """Return a compact summary of the most recent workflow runs."""
    cfg = cfg or load_config()
    params = {"per_page": str(max(1, min(int(limit), 30)))}
    with httpx.Client(timeout=15.0) as client:
        response = client.get(cfg.runs_url, headers=_headers(cfg), params=params)
    if response.status_code != 200:
        raise GitHubActionsError(
            f"list runs failed: HTTP {response.status_code} {response.text}"
        )
    data = response.json()
    runs = data.get("workflow_runs", []) or []
    summary: list[dict[str, Any]] = []
    for run in runs:
        summary.append(
            {
                "id": run.get("id"),
                "name": run.get("name") or run.get("display_title"),
                "status": run.get("status"),
                "conclusion": run.get("conclusion"),
                "event": run.get("event"),
                "created_at": run.get("created_at"),
                "updated_at": run.get("updated_at"),
                "run_started_at": run.get("run_started_at"),
                "html_url": run.get("html_url"),
            }
        )
    return summary
