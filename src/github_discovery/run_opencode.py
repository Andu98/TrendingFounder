from __future__ import annotations

import argparse

from src.github_discovery.client import DEFAULT_TARGET_LIMIT, DEFAULT_TOPIC, GITHUB_TOPIC_SOURCE_URL
from src.github_discovery.crawler import GitHubOpencodeCrawler


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Crawl GitHub repositories from the opencode topic.")
    parser.add_argument("--topic", default=DEFAULT_TOPIC, help="GitHub topic to search. Defaults to opencode.")
    parser.add_argument("--limit", type=int, default=DEFAULT_TARGET_LIMIT, help="Maximum repositories to fetch.")
    return parser.parse_args(argv)


def cli(argv: list[str] | None = None) -> int:
    args = parse_args(argv)

    def print_progress(message: str) -> None:
        print(message, flush=True)

    crawler = GitHubOpencodeCrawler(
        topic=args.topic,
        target_limit=args.limit,
        source_url=GITHUB_TOPIC_SOURCE_URL if args.topic == DEFAULT_TOPIC else f"https://github.com/topics/{args.topic}",
        progress=print_progress,
    )
    summary = crawler.run()
    print(f"status={summary.status}")
    print(f"fetched_count={summary.fetched_count}")
    print(f"new_count={summary.new_count}")
    print(f"baseline_count={summary.baseline_count}")
    print(f"run_id={summary.run_id}")
    return 0


if __name__ == "__main__":
    raise SystemExit(cli())
