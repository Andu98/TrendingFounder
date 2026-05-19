from __future__ import annotations

import subprocess
import sys
from pathlib import Path


def _project_root() -> Path:
    return Path(__file__).resolve().parents[1]


def _print_usage() -> None:
    print("Usage:")
    print("  start trending [streamlit args]")
    print("  start crawl-github-opencode [options]")
    print()
    print("Examples:")
    print("  start trending")
    print("  start trending --server.port 8502")


def start() -> int:
    """Entry point for the project's command-line interface.

    Supported sub-commands:
    * ``trending`` – launches the Streamlit dashboard (original behaviour).
    * ``crawl-github-opencode`` – fetches the GitHub opencode topic snapshot.
    * ``update-opportunity-scores`` – recalculates opportunity scores for all
      domains. Optional flags:
        ``--only-missing`` ``--limit N`` ``--min-trend-score X`` ``--dry-run``
        ``--force`` ``--fetch-homepage`` ``--concurrency N``
        ``--llm-concurrency N``
    """
    args = sys.argv[1:]
    if not args:
        _print_usage()
        return 2

    sub_cmd = args[0]

    if sub_cmd == "trending":
        # Preserve original behaviour
        root = _project_root()
        streamlit_app = root / "app" / "streamlit_app.py"
        command = [sys.executable, "-m", "streamlit", "run", str(streamlit_app), *args[1:]]
        return subprocess.call(command, cwd=root)

    if sub_cmd == "update-opportunity-scores":
        from src.opportunity.update_opportunity_scores import cli as opportunity_cli
        return opportunity_cli(argv=args[1:])

    if sub_cmd == "crawl-github-opencode":
        from src.github_discovery.run_opencode import cli as github_cli
        return github_cli(argv=args[1:])

    print(f"Unknown command: {sub_cmd}")
    _print_usage()
    return 2


if __name__ == "__main__":
    raise SystemExit(start())
