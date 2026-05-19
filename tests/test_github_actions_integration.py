import json

import httpx
import pytest

from src.integrations import github_actions as ga


@pytest.fixture
def cfg() -> ga.WorkflowConfig:
    return ga.WorkflowConfig(repo="owner/repo", token="t", workflow="crawl.yml", ref="main")


def test_load_config_missing(monkeypatch):
    for name in ("GH_REPO", "GH_DISPATCH_TOKEN", "GH_WORKFLOW_FILE", "GH_WORKFLOW_REF"):
        monkeypatch.delenv(name, raising=False)
    with pytest.raises(ga.GitHubActionsError):
        ga.load_config()


def test_load_config_from_env(monkeypatch):
    monkeypatch.setenv("GH_REPO", "owner/repo")
    monkeypatch.setenv("GH_DISPATCH_TOKEN", "tok")
    cfg = ga.load_config()
    assert cfg.repo == "owner/repo"
    assert cfg.token == "tok"
    assert cfg.workflow == "crawl.yml"
    assert cfg.ref == "main"


def test_trigger_workflow_posts_inputs(monkeypatch, cfg):
    captured = {}
    original_client = httpx.Client

    def handler(request: httpx.Request) -> httpx.Response:
        captured["url"] = str(request.url)
        captured["headers"] = dict(request.headers)
        captured["json"] = json.loads(request.content)
        return httpx.Response(204)

    transport = httpx.MockTransport(handler)
    monkeypatch.setattr(ga.httpx, "Client", lambda **_: original_client(transport=transport))

    ga.trigger_workflow(skip_domain=True, skip_github=False, skip_score=True, cfg=cfg)

    assert captured["url"].endswith("/actions/workflows/crawl.yml/dispatches")
    assert captured["headers"]["authorization"] == "Bearer t"
    assert captured["json"] == {
        "ref": "main",
        "inputs": {"skip_domain": "true", "skip_github": "false", "skip_score": "true"},
    }


def test_trigger_workflow_raises_on_error(monkeypatch, cfg):
    original_client = httpx.Client
    transport = httpx.MockTransport(lambda req: httpx.Response(422, text="bad"))
    monkeypatch.setattr(ga.httpx, "Client", lambda **_: original_client(transport=transport))
    with pytest.raises(ga.GitHubActionsError):
        ga.trigger_workflow(cfg=cfg)


def test_list_recent_runs_summary(monkeypatch, cfg):
    payload = {
        "workflow_runs": [
            {
                "id": 1,
                "name": "Crawl",
                "status": "completed",
                "conclusion": "success",
                "event": "workflow_dispatch",
                "created_at": "2026-05-19T08:00:00Z",
                "run_started_at": "2026-05-19T08:00:05Z",
                "updated_at": "2026-05-19T08:10:00Z",
                "html_url": "https://github.com/owner/repo/actions/runs/1",
            }
        ]
    }
    transport = httpx.MockTransport(lambda req: httpx.Response(200, json=payload))
    original_client = httpx.Client
    monkeypatch.setattr(ga.httpx, "Client", lambda **_: original_client(transport=transport))
    runs = ga.list_recent_runs(limit=3, cfg=cfg)
    assert len(runs) == 1
    assert runs[0]["conclusion"] == "success"
    assert runs[0]["html_url"].endswith("/runs/1")
