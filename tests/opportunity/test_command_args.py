"""Tests for opportunity scoring command arguments."""

import argparse
from src.opportunity.update_opportunity_scores import cli


def test_cli_default_args(monkeypatch):
    """Test that CLI parses default arguments correctly."""
    monkeypatch.setattr("sys.argv", ["main.py", "update-opportunity-scores"])
    
    parser = argparse.ArgumentParser()
    parser.add_argument("--only-missing", action="store_true")
    parser.add_argument("--limit", type=int)
    parser.add_argument("--min-trend-score", type=float)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--force", action="store_true")
    parser.add_argument("--fetch-homepage", action="store_true")
    parser.add_argument("--concurrency", type=int, default=5)
    
    args = parser.parse_args([])
    
    assert not args.only_missing
    assert args.limit is None
    assert args.min_trend_score is None
    assert not args.dry_run
    assert not args.force
    assert not args.fetch_homepage
    assert args.concurrency == 5


def test_cli_all_flags(monkeypatch):
    """Test that CLI parses all flags correctly."""
    parser = argparse.ArgumentParser()
    parser.add_argument("--only-missing", action="store_true")
    parser.add_argument("--limit", type=int)
    parser.add_argument("--min-trend-score", type=float)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--force", action="store_true")
    parser.add_argument("--fetch-homepage", action="store_true")
    parser.add_argument("--concurrency", type=int, default=5)
    
    args = parser.parse_args([
        "--only-missing",
        "--limit", "10",
        "--min-trend-score", "50.0",
        "--dry-run",
        "--force",
        "--fetch-homepage",
        "--concurrency", "3",
    ])
    
    assert args.only_missing
    assert args.limit == 10
    assert args.min_trend_score == 50.0
    assert args.dry_run
    assert args.force
    assert args.fetch_homepage
    assert args.concurrency == 3
