#!/usr/bin/env -S uv run
# /// script
# dependencies = ["pydantic>=2.0"]
# ///

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))
from grammatic.models import BuildLogEntry, ParseLogEntry


def count_nodes(node: dict[str, Any]) -> int:
    """Count all nodes in a parse tree recursively."""
    count = 1
    for child in node.get("children", []):
        count += count_nodes(child)
    return count


def has_errors(node: dict[str, Any]) -> bool:
    """Detect whether any node in the parse tree has type ERROR."""
    if node.get("type") == "ERROR":
        return True
    return any(has_errors(child) for child in node.get("children", []))


def lookup_grammar_version(grammar: str, builds_log_path: Path = Path("logs/builds.jsonl")) -> str:
    """Find most recent commit for a grammar from builds JSONL logs."""
    if not builds_log_path.exists():
        return "unknown"

    latest_commit = "unknown"

    try:
        with builds_log_path.open(encoding="utf-8") as handle:
            for line in handle:
                if not line.strip():
                    continue
                entry = json.loads(line)
                if entry.get("grammar") == grammar:
                    latest_commit = str(entry.get("commit", "unknown"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:  # pragma: no cover - warning path only
        print(f"Warning: Could not lookup grammar version: {exc}", file=sys.stderr)
        return "unknown"

    return latest_commit


def detect_compiler(grammar: str) -> str:
    """Detect compiler based on scanner file presence in grammar source."""
    grammar_dir = Path("grammars") / grammar
    if (grammar_dir / "src" / "scanner.cc").exists():
        return "g++"
    if (grammar_dir / "src" / "scanner.c").exists():
        return "gcc"
    return "gcc"


def log_build(args: argparse.Namespace) -> None:
    """Write build event JSON to stdout."""
    so_path = Path(args.so_path)
    entry = BuildLogEntry(
        timestamp=datetime.now(),
        grammar=args.grammar,
        commit=args.commit,
        repo_url=args.repo_url,
        so_path=so_path,
        build_success=True,
        build_time_ms=args.build_time,
        compiler=detect_compiler(args.grammar),
        tree_sitter_version=args.tree_sitter_version,
    )
    print(entry.model_dump_json())


def log_parse(args: argparse.Namespace) -> None:
    """Write parse event JSON to stdout."""
    parse_data = json.loads(Path(args.parse_result).read_text())
    root = parse_data.get("root_node", {})

    entry = ParseLogEntry(
        timestamp=datetime.now(),
        grammar=args.grammar,
        grammar_version=lookup_grammar_version(args.grammar),
        source_file=Path(args.source),
        node_count=count_nodes(root),
        has_errors=has_errors(root),
        parse_time_ms=args.parse_time,
        root_node_type=root.get("type", "unknown"),
    )
    print(entry.model_dump_json())


def main() -> None:
    parser = argparse.ArgumentParser(description="Log grammar build/parse events as JSONL")
    subparsers = parser.add_subparsers(dest="command", required=True)

    build_parser = subparsers.add_parser("build", help="Log build event")
    build_parser.add_argument("--grammar", required=True)
    build_parser.add_argument("--commit", required=True)
    build_parser.add_argument("--repo-url", required=True)
    build_parser.add_argument("--so-path", required=True)
    build_parser.add_argument("--build-time", required=True, type=int)
    build_parser.add_argument("--tree-sitter-version", required=True)

    parse_parser = subparsers.add_parser("parse", help="Log parse event")
    parse_parser.add_argument("--grammar", required=True)
    parse_parser.add_argument("--source", required=True)
    parse_parser.add_argument("--parse-result", required=True)
    parse_parser.add_argument("--parse-time", required=True, type=int)

    args = parser.parse_args()

    if args.command == "build":
        log_build(args)
    else:
        log_parse(args)


if __name__ == "__main__":
    main()
