from __future__ import annotations

import subprocess
import sys
from pathlib import Path


def _project_root() -> Path:
    return Path(__file__).resolve().parents[1]


def _print_usage() -> None:
    print("Usage:")
    print("  start trending [streamlit args]")
    print()
    print("Examples:")
    print("  start trending")
    print("  start trending --server.port 8502")


def start() -> int:
    args = sys.argv[1:]
    if not args or args[0] != "trending":
        _print_usage()
        return 2

    root = _project_root()
    streamlit_app = root / "app" / "streamlit_app.py"
    command = [sys.executable, "-m", "streamlit", "run", str(streamlit_app), *args[1:]]
    return subprocess.call(command, cwd=root)


if __name__ == "__main__":
    raise SystemExit(start())
