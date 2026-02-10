# Phase 3: Logging Infrastructure

## Scope
Implement log_writer.py as UV script to validate and write build/parse events to JSONL files.

## Dependencies
- Phase 1 complete (data models available)
- Phase 2 complete (build script for test fixtures)

## Deliverables

### 1. Log Writer Script

**File: `scripts/log_writer.py`**
```python
#!/usr/bin/env -S uv run
# /// script
# dependencies = ["pydantic>=2.0"]
# ///
# scripts/log_writer.py

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path

# Import from src/grammatic/models.py
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))
from grammatic.models import BuildLogEntry, ParseLogEntry


def log_build(args: argparse.Namespace) -> None:
    """Write build event to stdout as JSONL."""
    grammar_dir = Path(args.so_path).parent.parent / "grammars" / args.grammar

    # Detect compiler from scanner file
    if (grammar_dir / "src" / "scanner.cc").exists():
        compiler = "g++"
    else:
        compiler = "gcc"

    entry = BuildLogEntry(
        timestamp=datetime.now(),
        grammar=args.grammar,
        commit=args.commit,
        repo_url=args.repo_url,
        so_path=Path(args.so_path),
        build_success=True,  # Only called on successful build
        build_time_ms=args.build_time,
        compiler=compiler,
        tree_sitter_version=args.tree_sitter_version,
    )

    print(entry.model_dump_json())


def log_parse(args: argparse.Namespace) -> None:
    """Write parse event to stdout as JSONL."""
    # Load parse result JSON from tree-sitter
    with open(args.parse_result) as f:
        parse_data = json.load(f)

    # Count nodes recursively
    def count_nodes(node: dict) -> int:
        count = 1
        for child in node.get("children", []):
            count += count_nodes(child)
        return count

    # Check for ERROR nodes recursively
    def has_errors(node: dict) -> bool:
        if node.get("type") == "ERROR":
            return True
        return any(has_errors(child) for child in node.get("children", []))

    root = parse_data.get("root_node", {})

    # Lookup grammar version from most recent build log
    grammar_version = "unknown"
    try:
        builds_log = Path("logs/builds.jsonl")
        if builds_log.exists():
            # Read backwards to find most recent build
            with open(builds_log) as f:
                for line in reversed(list(f)):
                    entry = json.loads(line)
                    if entry["grammar"] == args.grammar:
                        grammar_version = entry["commit"]
                        break
    except Exception as e:
        print(f"Warning: Could not lookup grammar version: {e}", file=sys.stderr)

    entry = ParseLogEntry(
        timestamp=datetime.now(),
        grammar=args.grammar,
        grammar_version=grammar_version,
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

    # Build event subcommand
    build_parser = subparsers.add_parser("build", help="Log build event")
    build_parser.add_argument("--grammar", required=True)
    build_parser.add_argument("--commit", required=True)
    build_parser.add_argument("--repo-url", required=True)
    build_parser.add_argument("--so-path", required=True)
    build_parser.add_argument("--build-time", type=int, required=True)
    build_parser.add_argument("--tree-sitter-version", required=True)

    # Parse event subcommand
    parse_parser = subparsers.add_parser("parse", help="Log parse event")
    parse_parser.add_argument("--grammar", required=True)
    parse_parser.add_argument("--source", required=True)
    parse_parser.add_argument("--parse-result", required=True)
    parse_parser.add_argument("--parse-time", type=int, required=True)

    args = parser.parse_args()

    if args.command == "build":
        log_build(args)
    elif args.command == "parse":
        log_parse(args)


if __name__ == "__main__":
    main()
```

### 2. Test Fixtures

**File: `tests/fixtures/sample_parse.json`**
```json
{
  "root_node": {
    "type": "source_file",
    "children": [
      {
        "type": "line",
        "children": []
      },
      {
        "type": "line",
        "children": []
      }
    ]
  }
}
```

**File: `tests/fixtures/sample_parse_with_errors.json`**
```json
{
  "root_node": {
    "type": "source_file",
    "children": [
      {
        "type": "ERROR",
        "children": []
      }
    ]
  }
}
```

## Verification Tests

**File: `tests/test_log_writer.py`**
```python
# tests/test_log_writer.py
from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pytest


class TestLogWriter:
    def test_build_log_generation(self, tmp_path):
        """Generate valid build log entry."""
        result = subprocess.run(
            [
                "python",
                "scripts/log_writer.py",
                "build",
                "--grammar",
                "test",
                "--commit",
                "abc123",
                "--repo-url",
                "https://example.com/test",
                "--so-path",
                "build/test.so",
                "--build-time",
                "1234",
                "--tree-sitter-version",
                "0.21.0",
            ],
            capture_output=True,
            text=True,
            check=True,
        )

        # Parse output as JSON
        log_entry = json.loads(result.stdout)

        assert log_entry["event_type"] == "build"
        assert log_entry["grammar"] == "test"
        assert log_entry["commit"] == "abc123"
        assert log_entry["build_success"] is True
        assert log_entry["build_time_ms"] == 1234

    def test_parse_log_generation(self, tmp_path):
        """Generate valid parse log entry."""
        # Create test parse result
        parse_result = tmp_path / "parse.json"
        parse_result.write_text(
            json.dumps(
                {
                    "root_node": {
                        "type": "module",
                        "children": [{"type": "line", "children": []}],
                    }
                }
            )
        )

        result = subprocess.run(
            [
                "python",
                "scripts/log_writer.py",
                "parse",
                "--grammar",
                "test",
                "--source",
                "test.py",
                "--parse-result",
                str(parse_result),
                "--parse-time",
                "12",
            ],
            capture_output=True,
            text=True,
            check=True,
        )

        # Parse output as JSON
        log_entry = json.loads(result.stdout)

        assert log_entry["event_type"] == "parse"
        assert log_entry["grammar"] == "test"
        assert log_entry["node_count"] == 2
        assert log_entry["has_errors"] is False
        assert log_entry["root_node_type"] == "module"

    def test_parse_log_detects_errors(self, tmp_path):
        """Detect ERROR nodes in parse tree."""
        parse_result = tmp_path / "parse.json"
        parse_result.write_text(
            json.dumps({"root_node": {"type": "ERROR", "children": []}})
        )

        result = subprocess.run(
            [
                "python",
                "scripts/log_writer.py",
                "parse",
                "--grammar",
                "test",
                "--source",
                "test.py",
                "--parse-result",
                str(parse_result),
                "--parse-time",
                "12",
            ],
            capture_output=True,
            text=True,
            check=True,
        )

        log_entry = json.loads(result.stdout)
        assert log_entry["has_errors"] is True

    def test_node_counting(self, tmp_path):
        """Count nodes recursively."""
        parse_result = tmp_path / "parse.json"
        parse_result.write_text(
            json.dumps(
                {
                    "root_node": {
                        "type": "source",
                        "children": [
                            {"type": "a", "children": []},
                            {
                                "type": "b",
                                "children": [
                                    {"type": "c", "children": []},
                                    {"type": "d", "children": []},
                                ],
                            },
                        ],
                    }
                }
            )
        )

        result = subprocess.run(
            [
                "python",
                "scripts/log_writer.py",
                "parse",
                "--grammar",
                "test",
                "--source",
                "test.txt",
                "--parse-result",
                str(parse_result),
                "--parse-time",
                "5",
            ],
            capture_output=True,
            text=True,
            check=True,
        )

        log_entry = json.loads(result.stdout)
        assert log_entry["node_count"] == 5  # source + a + b + c + d

    def test_grammar_version_lookup(self, tmp_path, monkeypatch):
        """Lookup grammar version from builds.jsonl."""
        # Create logs directory with builds.jsonl
        logs_dir = tmp_path / "logs"
        logs_dir.mkdir()
        builds_log = logs_dir / "builds.jsonl"

        builds_log.write_text(
            json.dumps({"grammar": "test", "commit": "xyz789"}) + "\n"
        )

        parse_result = tmp_path / "parse.json"
        parse_result.write_text(
            json.dumps({"root_node": {"type": "module", "children": []}})
        )

        # Change to tmp_path so logs/builds.jsonl is found
        monkeypatch.chdir(tmp_path)

        result = subprocess.run(
            [
                "python",
                str(Path.cwd() / "scripts" / "log_writer.py"),
                "parse",
                "--grammar",
                "test",
                "--source",
                "test.py",
                "--parse-result",
                str(parse_result),
                "--parse-time",
                "12",
            ],
            capture_output=True,
            text=True,
            check=True,
        )

        log_entry = json.loads(result.stdout)
        assert log_entry["grammar_version"] == "xyz789"

    def test_missing_builds_log(self, tmp_path):
        """Handle missing builds.jsonl gracefully."""
        parse_result = tmp_path / "parse.json"
        parse_result.write_text(
            json.dumps({"root_node": {"type": "module", "children": []}})
        )

        result = subprocess.run(
            [
                "python",
                "scripts/log_writer.py",
                "parse",
                "--grammar",
                "test",
                "--source",
                "test.py",
                "--parse-result",
                str(parse_result),
                "--parse-time",
                "12",
            ],
            capture_output=True,
            text=True,
            check=True,
        )

        log_entry = json.loads(result.stdout)
        assert log_entry["grammar_version"] == "unknown"


class TestLogValidation:
    def test_valid_jsonl_format(self, tmp_path):
        """Ensure output is valid JSONL."""
        result = subprocess.run(
            [
                "python",
                "scripts/log_writer.py",
                "build",
                "--grammar",
                "test",
                "--commit",
                "abc",
                "--repo-url",
                "https://example.com",
                "--so-path",
                "test.so",
                "--build-time",
                "100",
                "--tree-sitter-version",
                "0.21.0",
            ],
            capture_output=True,
            text=True,
            check=True,
        )

        # Should be single line, valid JSON
        lines = result.stdout.strip().split("\n")
        assert len(lines) == 1
        json.loads(lines[0])  # Should not raise

    def test_append_to_log_file(self, tmp_path):
        """Append multiple entries to log file."""
        log_file = tmp_path / "test.jsonl"

        for i in range(3):
            result = subprocess.run(
                [
                    "python",
                    "scripts/log_writer.py",
                    "build",
                    "--grammar",
                    f"test{i}",
                    "--commit",
                    f"commit{i}",
                    "--repo-url",
                    "https://example.com",
                    "--so-path",
                    "test.so",
                    "--build-time",
                    "100",
                    "--tree-sitter-version",
                    "0.21.0",
                ],
                stdout=open(log_file, "a"),
                check=True,
            )

        # Read back all entries
        with open(log_file) as f:
            entries = [json.loads(line) for line in f]

        assert len(entries) == 3
        assert entries[0]["grammar"] == "test0"
        assert entries[2]["grammar"] == "test2"
```

## Acceptance Criteria

- [ ] Script executable with UV script header
- [ ] Build events logged with all required fields
- [ ] Parse events logged with node counting
- [ ] ERROR nodes detected correctly
- [ ] Grammar version looked up from builds.jsonl
- [ ] Missing builds.jsonl handled gracefully
- [ ] Output is valid JSONL (one JSON object per line)
- [ ] All tests pass (`pytest tests/test_log_writer.py -v`)

## Run Tests

```bash
devenv shell
pytest tests/test_log_writer.py -v
```
