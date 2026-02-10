# Phase 6: Query & Analysis

## Scope
Implement jq-based log query targets for analyzing build/parse history, computing metrics, and exporting logs.

## Dependencies
- Phase 1-5 complete (logs being generated)

## Deliverables

### 1. Query Targets

**Add to `justfile`:**
```makefile
# Query recent builds
query-builds N="10":
    jq -c '.' logs/builds.jsonl | tail -n {{N}}

# Query builds for specific grammar
query-builds-for GRAMMAR:
    jq -c "select(.grammar == \"{{GRAMMAR}}\")" logs/builds.jsonl

# Query recent parses
query-parses N="10":
    jq -c '.' logs/parses.jsonl | tail -n {{N}}

# Query parse failures
query-failures:
    jq -c 'select(.has_errors == true)' logs/parses.jsonl

# Query parses for specific grammar
query-parses-for GRAMMAR:
    jq -c "select(.grammar == \"{{GRAMMAR}}\")" logs/parses.jsonl

# Build success rate for grammar
build-success-rate GRAMMAR:
    #!/usr/bin/env bash
    jq -c "select(.grammar == \"{{GRAMMAR}}\")" logs/builds.jsonl \
        | jq -s "group_by(.build_success) | map({success: .[0].build_success, count: length})"

# Average parse time for grammar
avg-parse-time GRAMMAR:
    #!/usr/bin/env bash
    jq -c "select(.grammar == \"{{GRAMMAR}}\")" logs/parses.jsonl \
        | jq -s 'map(.parse_time_ms) | add / length'

# Slowest parses
slowest-parses N="10":
    #!/usr/bin/env bash
    jq -c '.' logs/parses.jsonl \
        | jq -s "sort_by(.parse_time_ms) | reverse | .[:{{N}}]"

# Grammar version distribution
grammar-versions GRAMMAR:
    #!/usr/bin/env bash
    jq -c "select(.grammar == \"{{GRAMMAR}}\")" logs/parses.jsonl \
        | jq -r '.grammar_version' \
        | sort | uniq -c

# Export logs as tarball
export-logs OUTPUT:
    #!/usr/bin/env bash
    TIMESTAMP=$(date +%Y%m%d-%H%M%S)
    tar czf {{OUTPUT}}/grammatic-logs-$TIMESTAMP.tar.gz logs/*.jsonl
    echo "Logs exported to {{OUTPUT}}/grammatic-logs-$TIMESTAMP.tar.gz"

# Validate log files have valid JSON
validate-logs:
    #!/usr/bin/env bash
    echo "Validating builds.jsonl..."
    if [ -f logs/builds.jsonl ]; then
        jq -e '.' logs/builds.jsonl > /dev/null || echo "builds.jsonl has invalid JSON"
    fi
    echo "Validating parses.jsonl..."
    if [ -f logs/parses.jsonl ]; then
        jq -e '.' logs/parses.jsonl > /dev/null || echo "parses.jsonl has invalid JSON"
    fi
    echo "Log validation complete"
```

### 2. Helper Script for Complex Queries

**File: `scripts/query_logs.py`**
```python
#!/usr/bin/env -S uv run
# /// script
# dependencies = ["pydantic>=2.0"]
# ///
# scripts/query_logs.py

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path
from statistics import mean, median


def load_jsonl(path: Path) -> list[dict]:
    """Load JSONL file as list of dicts."""
    if not path.exists():
        return []
    with open(path) as f:
        return [json.loads(line) for line in f]


def summary_stats(args: argparse.Namespace) -> None:
    """Print summary statistics for logs."""
    builds = load_jsonl(Path("logs/builds.jsonl"))
    parses = load_jsonl(Path("logs/parses.jsonl"))

    print(f"Total builds: {len(builds)}")
    print(f"Total parses: {len(parses)}")

    if builds:
        success_rate = sum(1 for b in builds if b["build_success"]) / len(builds) * 100
        print(f"Build success rate: {success_rate:.1f}%")

        build_times = [b["build_time_ms"] for b in builds]
        print(f"Avg build time: {mean(build_times):.1f}ms")
        print(f"Median build time: {median(build_times):.1f}ms")

    if parses:
        error_rate = sum(1 for p in parses if p["has_errors"]) / len(parses) * 100
        print(f"Parse error rate: {error_rate:.1f}%")

        parse_times = [p["parse_time_ms"] for p in parses]
        print(f"Avg parse time: {mean(parse_times):.1f}ms")
        print(f"Median parse time: {median(parse_times):.1f}ms")


def grammar_stats(args: argparse.Namespace) -> None:
    """Print per-grammar statistics."""
    builds = load_jsonl(Path("logs/builds.jsonl"))
    parses = load_jsonl(Path("logs/parses.jsonl"))

    # Group by grammar
    grammar_builds = defaultdict(list)
    grammar_parses = defaultdict(list)

    for b in builds:
        grammar_builds[b["grammar"]].append(b)

    for p in parses:
        grammar_parses[p["grammar"]].append(p)

    # Print stats per grammar
    all_grammars = set(grammar_builds.keys()) | set(grammar_parses.keys())

    for grammar in sorted(all_grammars):
        print(f"\n{grammar}:")
        print(f"  Builds: {len(grammar_builds[grammar])}")
        print(f"  Parses: {len(grammar_parses[grammar])}")

        if grammar_builds[grammar]:
            success_rate = sum(1 for b in grammar_builds[grammar] if b["build_success"]) / len(
                grammar_builds[grammar]
            ) * 100
            print(f"  Build success rate: {success_rate:.1f}%")

        if grammar_parses[grammar]:
            error_rate = sum(1 for p in grammar_parses[grammar] if p["has_errors"]) / len(
                grammar_parses[grammar]
            ) * 100
            print(f"  Parse error rate: {error_rate:.1f}%")


def timeline(args: argparse.Namespace) -> None:
    """Print event timeline."""
    builds = load_jsonl(Path("logs/builds.jsonl"))
    parses = load_jsonl(Path("logs/parses.jsonl"))

    # Combine and sort by timestamp
    events = []
    for b in builds:
        events.append((datetime.fromisoformat(b["timestamp"]), "BUILD", b["grammar"]))
    for p in parses:
        events.append((datetime.fromisoformat(p["timestamp"]), "PARSE", p["grammar"]))

    events.sort()

    for timestamp, event_type, grammar in events[-args.limit :]:
        print(f"{timestamp.strftime('%Y-%m-%d %H:%M:%S')} | {event_type:6} | {grammar}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Query grammatic logs")
    subparsers = parser.add_subparsers(dest="command", required=True)

    # Summary stats
    subparsers.add_parser("summary", help="Print summary statistics")

    # Grammar stats
    subparsers.add_parser("grammar-stats", help="Print per-grammar statistics")

    # Timeline
    timeline_parser = subparsers.add_parser("timeline", help="Print event timeline")
    timeline_parser.add_argument("--limit", type=int, default=20, help="Number of recent events")

    args = parser.parse_args()

    if args.command == "summary":
        summary_stats(args)
    elif args.command == "grammar-stats":
        grammar_stats(args)
    elif args.command == "timeline":
        timeline(args)


if __name__ == "__main__":
    main()
```

## Verification Tests

**File: `tests/test_queries.py`**
```python
# tests/test_queries.py
from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pytest


@pytest.fixture
def repo_with_logs(test_repo):
    """Create repo with sample log data."""
    subprocess.run(["just", "init"], check=True, capture_output=True, cwd=test_repo)

    # Create sample builds.jsonl
    builds_log = test_repo / "logs" / "builds.jsonl"
    builds_log.write_text(
        json.dumps(
            {
                "event_type": "build",
                "grammar": "test",
                "build_success": True,
                "build_time_ms": 100,
                "timestamp": "2026-01-01T10:00:00",
            }
        )
        + "\n"
        + json.dumps(
            {
                "event_type": "build",
                "grammar": "test",
                "build_success": False,
                "build_time_ms": 150,
                "timestamp": "2026-01-01T11:00:00",
            }
        )
        + "\n"
        + json.dumps(
            {
                "event_type": "build",
                "grammar": "other",
                "build_success": True,
                "build_time_ms": 200,
                "timestamp": "2026-01-01T12:00:00",
            }
        )
        + "\n"
    )

    # Create sample parses.jsonl
    parses_log = test_repo / "logs" / "parses.jsonl"
    parses_log.write_text(
        json.dumps(
            {
                "event_type": "parse",
                "grammar": "test",
                "has_errors": False,
                "parse_time_ms": 10,
                "timestamp": "2026-01-01T13:00:00",
            }
        )
        + "\n"
        + json.dumps(
            {
                "event_type": "parse",
                "grammar": "test",
                "has_errors": True,
                "parse_time_ms": 20,
                "timestamp": "2026-01-01T14:00:00",
            }
        )
        + "\n"
    )

    return test_repo


class TestLogQueries:
    def test_query_builds(self, repo_with_logs):
        """Query all builds."""
        result = subprocess.run(
            ["just", "query-builds", "10"], capture_output=True, text=True, check=True, cwd=repo_with_logs
        )

        lines = result.stdout.strip().split("\n")
        assert len(lines) == 3

    def test_query_builds_for_grammar(self, repo_with_logs):
        """Query builds for specific grammar."""
        result = subprocess.run(
            ["just", "query-builds-for", "test"],
            capture_output=True,
            text=True,
            check=True,
            cwd=repo_with_logs,
        )

        lines = result.stdout.strip().split("\n")
        assert len(lines) == 2
        assert all("test" in line for line in lines)

    def test_query_parses(self, repo_with_logs):
        """Query all parses."""
        result = subprocess.run(
            ["just", "query-parses", "10"],
            capture_output=True,
            text=True,
            check=True,
            cwd=repo_with_logs,
        )

        lines = result.stdout.strip().split("\n")
        assert len(lines) == 2

    def test_query_failures(self, repo_with_logs):
        """Query only failed parses."""
        result = subprocess.run(
            ["just", "query-failures"],
            capture_output=True,
            text=True,
            check=True,
            cwd=repo_with_logs,
        )

        lines = result.stdout.strip().split("\n")
        assert len(lines) == 1
        entry = json.loads(lines[0])
        assert entry["has_errors"] is True

    def test_build_success_rate(self, repo_with_logs):
        """Calculate build success rate."""
        result = subprocess.run(
            ["just", "build-success-rate", "test"],
            capture_output=True,
            text=True,
            check=True,
            cwd=repo_with_logs,
        )

        rates = json.loads(result.stdout)
        assert len(rates) == 2  # One for True, one for False

    def test_avg_parse_time(self, repo_with_logs):
        """Calculate average parse time."""
        result = subprocess.run(
            ["just", "avg-parse-time", "test"],
            capture_output=True,
            text=True,
            check=True,
            cwd=repo_with_logs,
        )

        avg = float(result.stdout.strip())
        assert avg == 15.0  # (10 + 20) / 2


class TestLogValidation:
    def test_validate_valid_logs(self, repo_with_logs):
        """Validate correctly formatted logs."""
        result = subprocess.run(
            ["just", "validate-logs"],
            capture_output=True,
            text=True,
            check=True,
            cwd=repo_with_logs,
        )

        assert "validation complete" in result.stdout.lower()
        assert result.returncode == 0

    def test_validate_missing_logs(self, test_repo):
        """Handle missing log files gracefully."""
        subprocess.run(["just", "init"], check=True, capture_output=True, cwd=test_repo)

        result = subprocess.run(
            ["just", "validate-logs"],
            capture_output=True,
            text=True,
            check=True,
            cwd=test_repo,
        )

        assert result.returncode == 0


class TestLogExport:
    def test_export_logs(self, repo_with_logs, tmp_path):
        """Export logs as tarball."""
        output_dir = tmp_path / "exports"
        output_dir.mkdir()

        result = subprocess.run(
            ["just", "export-logs", str(output_dir)],
            capture_output=True,
            text=True,
            check=True,
            cwd=repo_with_logs,
        )

        assert "exported" in result.stdout.lower()

        # Check tarball exists
        tarballs = list(output_dir.glob("grammatic-logs-*.tar.gz"))
        assert len(tarballs) == 1

    def test_exported_tarball_contents(self, repo_with_logs, tmp_path):
        """Verify tarball contains log files."""
        output_dir = tmp_path / "exports"
        output_dir.mkdir()

        subprocess.run(
            ["just", "export-logs", str(output_dir)],
            check=True,
            capture_output=True,
            cwd=repo_with_logs,
        )

        tarball = list(output_dir.glob("grammatic-logs-*.tar.gz"))[0]

        # Extract and verify
        extract_dir = tmp_path / "extracted"
        extract_dir.mkdir()
        subprocess.run(["tar", "xzf", str(tarball), "-C", str(extract_dir)], check=True)

        assert (extract_dir / "logs" / "builds.jsonl").exists()
        assert (extract_dir / "logs" / "parses.jsonl").exists()


class TestComplexQueries:
    def test_query_logs_summary(self, repo_with_logs):
        """Get summary statistics."""
        result = subprocess.run(
            ["python", "scripts/query_logs.py", "summary"],
            capture_output=True,
            text=True,
            check=True,
            cwd=repo_with_logs,
        )

        assert "Total builds" in result.stdout
        assert "Total parses" in result.stdout
        assert "success rate" in result.stdout

    def test_query_logs_grammar_stats(self, repo_with_logs):
        """Get per-grammar statistics."""
        result = subprocess.run(
            ["python", "scripts/query_logs.py", "grammar-stats"],
            capture_output=True,
            text=True,
            check=True,
            cwd=repo_with_logs,
        )

        assert "test:" in result.stdout
        assert "other:" in result.stdout
```

## Acceptance Criteria

- [ ] `just query-builds` shows recent builds
- [ ] `just query-builds-for GRAMMAR` filters by grammar
- [ ] `just query-parses` shows recent parses
- [ ] `just query-failures` shows only errors
- [ ] `just build-success-rate` calculates percentage
- [ ] `just avg-parse-time` computes average
- [ ] `just export-logs` creates tarball
- [ ] `just validate-logs` checks JSON validity
- [ ] All tests pass (`pytest tests/test_queries.py -v`)

## Run Tests

```bash
devenv shell
pytest tests/test_queries.py -v
```
