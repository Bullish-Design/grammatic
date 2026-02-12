from __future__ import annotations

import json
from pathlib import Path

from grammatic.logs import LogRepository


def write_jsonl(path: Path, entries: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(json.dumps(entry) for entry in entries) + "\n", encoding="utf-8")


def test_recent_and_filtered_queries(tmp_path: Path) -> None:
    repo_root = tmp_path
    write_jsonl(
        repo_root / "logs" / "builds.jsonl",
        [
            {"event_type": "build", "grammar": "a", "status": "success", "duration_ms": 10, "timestamp": "2026-01-01T00:00:00"},
            {"event_type": "build", "grammar": "b", "status": "failure", "duration_ms": 20, "timestamp": "2026-01-01T00:01:00"},
            {"event_type": "build", "grammar": "a", "status": "success", "duration_ms": 30, "timestamp": "2026-01-01T00:02:00"},
        ],
    )
    write_jsonl(
        repo_root / "logs" / "parses.jsonl",
        [
            {"event_type": "parse", "grammar": "a", "status": "success", "has_errors": False, "duration_ms": 5, "timestamp": "2026-01-01T00:03:00"},
            {"event_type": "parse", "grammar": "a", "status": "success", "has_errors": True, "duration_ms": 15, "timestamp": "2026-01-01T00:04:00"},
            {"event_type": "parse", "grammar": "b", "status": "failure", "has_errors": False, "duration_ms": 25, "timestamp": "2026-01-01T00:05:00"},
        ],
    )

    repo = LogRepository(repo_root)

    recent_builds = repo.recent_builds(limit=2)
    assert [entry.grammar for entry in recent_builds] == ["b", "a"]

    filtered_builds = repo.recent_builds(limit=10, grammar="a")
    assert len(filtered_builds) == 2

    failures = repo.recent_parses(limit=10, failures_only=True)
    assert len(failures) == 2


def test_summary_metrics(tmp_path: Path) -> None:
    repo_root = tmp_path
    write_jsonl(
        repo_root / "logs" / "builds.jsonl",
        [
            {"event_type": "build", "grammar": "a", "status": "success", "duration_ms": 100, "timestamp": "2026-01-01T00:00:00"},
            {"event_type": "build", "grammar": "a", "status": "failure", "duration_ms": 300, "timestamp": "2026-01-01T00:01:00"},
        ],
    )
    write_jsonl(
        repo_root / "logs" / "parses.jsonl",
        [
            {"event_type": "parse", "grammar": "a", "status": "success", "has_errors": False, "duration_ms": 10, "timestamp": "2026-01-01T00:03:00"},
            {"event_type": "parse", "grammar": "a", "status": "success", "has_errors": True, "duration_ms": 30, "timestamp": "2026-01-01T00:04:00"},
        ],
    )

    repo = LogRepository(repo_root)

    build_metrics, build_counts = repo.build_metrics(grammar="a")
    assert build_metrics.total == 2
    assert build_metrics.success_rate == 50.0
    assert build_counts == {"success": 1, "failure": 1}

    parse_metrics, parse_counts = repo.parse_metrics(grammar="a")
    assert parse_metrics.total == 2
    assert parse_metrics.failure_count == 1
    assert parse_metrics.latency_ms["p50"] == 20.0
    assert parse_counts == {"success": 1, "failure": 1}
