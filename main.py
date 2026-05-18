"""Main entry point for the application."""

import sys
from pathlib import Path

def main():
    args = sys.argv[1:]
    if not args or args[0] != "update-opportunity-scores":
        print("Usage: python main.py update-opportunity-scores [options]")
        return 2
    from src.opportunity.update_opportunity_scores import cli
    return cli(argv=args[1:])

if __name__ == "__main__":
    raise SystemExit(main())