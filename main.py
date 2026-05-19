"""Main entry point for the application."""

import sys


def main():
    args = sys.argv[1:]
    if not args:
        print("Usage: python main.py <update-opportunity-scores|crawl-github-opencode> [options]")
        return 2

    if args[0] == "update-opportunity-scores":
        from src.opportunity.update_opportunity_scores import cli
        return cli(argv=args[1:])

    if args[0] == "crawl-github-opencode":
        from src.github_discovery.run_opencode import cli
        return cli(argv=args[1:])

    print(f"Unknown command: {args[0]}")
    print("Usage: python main.py <update-opportunity-scores|crawl-github-opencode> [options]")
    return 2

if __name__ == "__main__":
    raise SystemExit(main())
