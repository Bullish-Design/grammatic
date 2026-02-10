#!/usr/bin/env -S uv run
# /// script
# dependencies = ["pydantic>=2.0"]
# ///

from __future__ import annotations

import argparse
import json
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from statistics import mean, median
from typing import Any


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    """Load a JSONL log file into a list of dictionaries."""
    if not path.exists():
        return []

    entries: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        entries.append(json.loads(line))
    return entries


def summary_stats() -> None:
    """Print global summary statistics across build and parse logs."""
    builds = load_jsonl(Path("logs/builds.jsonl"))
    parses = load_jsonl(Path("logs/parses.jsonl"))

    print(f"Total builds: {len(builds)}")
    print(f"Total parses: {len(parses)}")

    if builds:
        success_rate = sum(1 for entry in builds if entry.get("build_success")) / len(builds) * 100
        print(f"Build success rate: {success_rate:.1f}%")

        build_times = [int(entry["build_time_ms"]) for entry in builds]
        print(f"Avg build time: {mean(build_times):.1f}ms")
        print(f"Median build time: {median(build_times):.1f}ms")

    if parses:
        error_rate = sum(1 for entry in parses if entry.get("has_errors")) / len(parses) * 100
        print(f"Parse error rate: {error_rate:.1f}%")

        parse_times = [int(entry["parse_time_ms"]) for entry in parses]
        print(f"Avg parse time: {mean(parse_times):.1f}ms")
        print(f"Median parse time: {median(parse_times):.1f}ms")


def grammar_stats() -> None:
    """Print per-grammar build/parse statistics."""
    builds = load_jsonl(Path("logs/builds.jsonl"))
    parses = load_jsonl(Path("logs/parses.jsonl"))

    grammar_builds: dict[str, list[dict[str, Any]]] = defaultdict(list)
    grammar_parses: dict[str, list[dict[str, Any]]] = defaultdict(list)

    for entry in builds:
        grammar_builds[str(entry["grammar"])].append(entry)

    for entry in parses:
        grammar_parses[str(entry["grammar"])].append(entry)

    for grammar in sorted(set(grammar_builds) | set(grammar_parses)):
        current_builds = grammar_builds[grammar]
        current_parses = grammar_parses[grammar]

        print(f"\n{grammar}:")
        print(f"  Builds: {len(current_builds)}")
        print(f"  Parses: {len(current_parses)}")

        if current_builds:
            success_rate = sum(1 for entry in current_builds if entry.get("build_success")) / len(current_builds) * 100
            print(f"  Build success rate: {success_rate:.1f}%")

        if current_parses:
            error_rate = sum(1 for entry in current_parses if entry.get("has_errors")) / len(current_parses) * 100
            print(f"  Parse error rate: {error_rate:.1f}%")


def timeline(limit: int) -> None:
    """Print a combined chronological event timeline."""
    builds = load_jsonl(Path("logs/builds.jsonl"))
    parses = load_jsonl(Path("logs/parses.jsonl"))

    events: list[tuple[datetime, str, str]] = []
    for entry in builds:
        events.append((datetime.fromisoformat(entry["timestamp"]), "BUILD", str(entry["grammar"])))
    for entry in parses:
        events.append((datetime.fromisoformat(entry["timestamp"]), "PARSE", str(entry["grammar"])))

    for timestamp, event_type, grammar in sorted(events)[-limit:]:
        print(f"{timestamp.strftime('%Y-%m-%d %H:%M:%S')} | {event_type:6} | {grammar}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Query grammatic logs")
    subparsers = parser.add_subparsers(dest="command", required=True)

    subparsers.add_parser("summary", help="Print summary statistics")
    subparsers.add_parser("grammar-stats", help="Print per-grammar statistics")

    timeline_parser = subparsers.add_parser("timeline", help="Print event timeline")
    timeline_parser.add_argument("--limit", type=int, default=20, help="Number of recent events")

    args = parser.parse_args()

    if args.command == "summary":
        summary_stats()
    elif args.command == "grammar-stats":
        grammar_stats()
    else:
        timeline(args.limit)


if __name__ == "__main__":
    main()
