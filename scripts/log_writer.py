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


def lookup_grammar_version(grammar: str, builds_log_path: Path) -> str:
    """Find most recent commit for a grammar from builds JSONL logs."""
    if not builds_log_path.exists():
        return "unknown"

    try:
        lines = builds_log_path.read_text().splitlines()
        for line in reversed(lines):
            if not line.strip():
                continue
            entry = json.loads(line)
            if entry.get("grammar") == grammar:
                return str(entry.get("commit", "unknown"))
    except Exception as exc:  # pragma: no cover - warning path only
        print(f"Warning: Could not lookup grammar version: {exc}", file=sys.stderr)

    return "unknown"


def detect_compiler(grammar: str, project_root: Path) -> str:
    """Detect compiler based on scanner file presence in grammar source."""
    grammar_dir = (project_root / "grammars" / grammar).resolve()
    if not grammar_dir.exists():
        raise FileNotFoundError(
            f"Grammar directory not found for '{grammar}': {grammar_dir}. "
            "Pass --project-root to set the repository root."
        )

    if (grammar_dir / "src" / "scanner.cc").exists():
        return "g++"
    if (grammar_dir / "src" / "scanner.c").exists():
        return "gcc"
    return "gcc"


def resolve_project_root(project_root_arg: str | None) -> Path:
    """Resolve project root from CLI arg or current working directory."""
    project_root = Path(project_root_arg).resolve() if project_root_arg else Path.cwd().resolve()
    if not project_root.exists() or not project_root.is_dir():
        raise FileNotFoundError(f"Project root directory does not exist: {project_root}")
    return project_root


def resolve_from_project_root(path_arg: str, project_root: Path) -> Path:
    """Resolve a possibly-relative path from project root."""
    path = Path(path_arg)
    if not path.is_absolute():
        path = project_root / path
    return path.resolve()


def log_build(args: argparse.Namespace) -> None:
    """Write build event JSON to stdout."""
    project_root = resolve_project_root(args.project_root)
    so_path = resolve_from_project_root(args.so_path, project_root)
    entry = BuildLogEntry(
        timestamp=datetime.now(),
        grammar=args.grammar,
        commit=args.commit,
        repo_url=args.repo_url,
        so_path=so_path,
        build_success=True,
        build_time_ms=args.build_time,
        compiler=detect_compiler(args.grammar, project_root),
        tree_sitter_version=args.tree_sitter_version,
    )
    print(entry.model_dump_json())


def log_parse(args: argparse.Namespace) -> None:
    """Write parse event JSON to stdout."""
    project_root = resolve_project_root(args.project_root)
    parse_result_path = resolve_from_project_root(args.parse_result, project_root)
    if not parse_result_path.exists():
        raise FileNotFoundError(f"Parse result file not found: {parse_result_path}")

    builds_log_path = (
        resolve_from_project_root(args.builds_log, project_root)
        if args.builds_log
        else (project_root / "logs" / "builds.jsonl").resolve()
    )
    if args.builds_log and not builds_log_path.exists():
        raise FileNotFoundError(f"Builds log file not found: {builds_log_path}")

    parse_data = json.loads(parse_result_path.read_text())
    root = parse_data.get("root_node", {})

    entry = ParseLogEntry(
        timestamp=datetime.now(),
        grammar=args.grammar,
        grammar_version=lookup_grammar_version(args.grammar, builds_log_path),
        source_file=resolve_from_project_root(args.source, project_root),
        node_count=count_nodes(root),
        has_errors=has_errors(root),
        parse_time_ms=args.parse_time,
        root_node_type=root.get("type", "unknown"),
    )
    print(entry.model_dump_json())


def main() -> None:
    parser = argparse.ArgumentParser(description="Log grammar build/parse events as JSONL")
    parser.add_argument("--project-root", help="Project root used to resolve relative paths")
    parser.add_argument("--builds-log", help="Path to builds JSONL (relative paths resolved from project root)")
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

    try:
        if args.command == "build":
            log_build(args)
        else:
            log_parse(args)
    except FileNotFoundError as exc:
        parser.error(str(exc))


if __name__ == "__main__":
    main()
