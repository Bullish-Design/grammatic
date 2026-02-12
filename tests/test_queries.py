from __future__ import annotations

import json
from pathlib import Path

import pytest

from grammatic.logs import LogRepository

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SPECIAL_GRAMMARS = ['quote"name', 'dollar$name', 'bracket[name]']
BASE_BUILD_ENTRIES = 4
BASE_PARSE_ENTRIES = 3
TOTAL_BUILD_ENTRIES = BASE_BUILD_ENTRIES + len(SPECIAL_GRAMMARS)
TOTAL_PARSE_ENTRIES = BASE_PARSE_ENTRIES + len(SPECIAL_GRAMMARS)


@pytest.fixture
def repo_with_logs(tmp_path: Path) -> Path:
    """Create a test repository with populated log files."""
    repo = tmp_path / "test_repo"
    repo.mkdir()
    (repo / "logs").mkdir()
    (repo / "grammars").mkdir()
    (repo / "build").mkdir()

    builds_log = repo / "logs" / "builds.jsonl"
    builds_log.write_text(
        "\n".join(
            [
                json.dumps(
                    {
                        "event_type": "build",
                        "grammar": "test",
                        "status": "success",
                        "duration_ms": 100,
                        "timestamp": "2026-01-01T10:00:00",
                    }
                ),
                json.dumps(
                    {
                        "event_type": "build",
                        "grammar": "test",
                        "status": "failure",
                        "duration_ms": 150,
                        "timestamp": "2026-01-01T11:00:00",
                    }
                ),
                json.dumps(
                    {
                        "event_type": "build",
                        "grammar": "other",
                        "status": "success",
                        "duration_ms": 200,
                        "timestamp": "2026-01-01T12:00:00",
                    }
                ),
                json.dumps(
                    {
                        "event_type": "build",
                        "grammar": 'odd"name$[]',
                        "status": "success",
                        "duration_ms": 90,
                        "timestamp": "2026-01-01T12:30:00",
                    }
                ),
                *[
                    json.dumps(
                        {
                            "event_type": "build",
                            "grammar": grammar,
                            "status": "success",
                            "duration_ms": 95,
                            "timestamp": "2026-01-01T12:45:00",
                        }
                    )
                    for grammar in SPECIAL_GRAMMARS
                ],
            ]
        )
        + "\n",
        encoding="utf-8",
    )

    parses_log = repo / "logs" / "parses.jsonl"
    parses_log.write_text(
        "\n".join(
            [
                json.dumps(
                    {
                        "event_type": "parse",
                        "grammar": "test",
                        "grammar_version": "abc123",
                        "has_errors": False,
                        "duration_ms": 10,
                        "timestamp": "2026-01-01T13:00:00",
                    }
                ),
                json.dumps(
                    {
                        "event_type": "parse",
                        "grammar": "test",
                        "grammar_version": "def456",
                        "has_errors": True,
                        "duration_ms": 20,
                        "timestamp": "2026-01-01T14:00:00",
                    }
                ),
                json.dumps(
                    {
                        "event_type": "parse",
                        "grammar": 'odd"name$[]',
                        "grammar_version": "ghi789",
                        "has_errors": False,
                        "duration_ms": 7,
                        "timestamp": "2026-01-01T14:30:00",
                    }
                ),
                *[
                    json.dumps(
                        {
                            "event_type": "parse",
                            "grammar": grammar,
                            "grammar_version": "xyz000",
                            "has_errors": False,
                            "duration_ms": 8,
                            "timestamp": "2026-01-01T15:00:00",
                        }
                    )
                    for grammar in SPECIAL_GRAMMARS
                ],
            ]
        )
        + "\n",
        encoding="utf-8",
    )

    return repo


class TestLogQueries:
    """Test LogRepository query methods using Python API directly."""

    def test_query_builds(self, repo_with_logs: Path) -> None:
        """Query recent builds with limit."""
        repo = LogRepository(repo_with_logs)
        entries = list(repo.recent_builds(limit=10))
        assert len(entries) == TOTAL_BUILD_ENTRIES

    def test_query_builds_for_grammar(self, repo_with_logs: Path) -> None:
        """Query builds filtered by grammar name."""
        repo = LogRepository(repo_with_logs)
        entries = list(repo.recent_builds(grammar="test"))

        assert len(entries) == 2
        assert all(entry.grammar == "test" for entry in entries)

    @pytest.mark.parametrize("grammar", ['odd"name$[]', *SPECIAL_GRAMMARS])
    def test_query_builds_for_grammar_with_special_chars(self, repo_with_logs: Path, grammar: str) -> None:
        """Query builds for grammars with special characters in name."""
        repo = LogRepository(repo_with_logs)
        entries = list(repo.recent_builds(grammar=grammar))

        assert len(entries) == 1
        assert entries[0].grammar == grammar

    @pytest.mark.parametrize("grammar", ['odd"name$[]', *SPECIAL_GRAMMARS])
    def test_query_parses_for_grammar_with_special_chars(self, repo_with_logs: Path, grammar: str) -> None:
        """Query parses for grammars with special characters in name."""
        repo = LogRepository(repo_with_logs)
        entries = list(repo.recent_parses(grammar=grammar))

        assert len(entries) == 1
        assert entries[0].grammar == grammar

    @pytest.mark.parametrize("grammar", ['odd"name$[]', *SPECIAL_GRAMMARS])
    def test_build_success_rate_with_special_chars(self, repo_with_logs: Path, grammar: str) -> None:
        """Calculate build success rate for grammars with special characters."""
        repo = LogRepository(repo_with_logs)
        metrics, status_counts = repo.build_metrics(grammar=grammar)

        assert metrics.total == 1
        assert metrics.success_count == 1
        assert metrics.failure_count == 0
        assert status_counts == {"success": 1}

    def test_query_parses(self, repo_with_logs: Path) -> None:
        """Query recent parses with limit."""
        repo = LogRepository(repo_with_logs)
        entries = list(repo.recent_parses(limit=10))
        assert len(entries) == TOTAL_PARSE_ENTRIES

    def test_query_failures(self, repo_with_logs: Path) -> None:
        """Query only failed parses."""
        repo = LogRepository(repo_with_logs)
        entries = list(repo.recent_parses(failures_only=True))

        assert len(entries) == 1
        assert entries[0].has_errors is True

    def test_build_success_rate(self, repo_with_logs: Path) -> None:
        """Calculate build success rate for a specific grammar."""
        repo = LogRepository(repo_with_logs)
        metrics, status_counts = repo.build_metrics(grammar="test")

        assert metrics.total == 2
        assert metrics.success_count == 1
        assert metrics.failure_count == 1
        assert status_counts == {"success": 1, "failure": 1}

    def test_avg_parse_time(self, repo_with_logs: Path) -> None:
        """Calculate average parse time."""
        repo = LogRepository(repo_with_logs)
        avg_duration = repo.parse_average_duration_ms(grammar="test")

        # Average of 10ms and 20ms is 15ms
        assert avg_duration == 15.0

    def test_build_metrics(self, repo_with_logs: Path) -> None:
        """Get build metrics for a grammar."""
        repo = LogRepository(repo_with_logs)
        metrics, status_counts = repo.build_metrics(grammar="test")

        assert metrics.total == 2
        assert metrics.success_count == 1
        assert metrics.failure_count == 1
        assert status_counts == {"success": 1, "failure": 1}

    def test_parse_metrics(self, repo_with_logs: Path) -> None:
        """Get parse metrics for a grammar."""
        repo = LogRepository(repo_with_logs)
        metrics, status_counts = repo.parse_metrics(grammar="test")

        assert metrics.total == 2
        assert metrics.success_count == 1
        assert metrics.failure_count == 1

    def test_recent_builds_no_filter(self, repo_with_logs: Path) -> None:
        """Query all builds without grammar filter."""
        repo = LogRepository(repo_with_logs)
        entries = list(repo.recent_builds(limit=None))
        assert len(entries) == TOTAL_BUILD_ENTRIES

    def test_recent_parses_no_filter(self, repo_with_logs: Path) -> None:
        """Query all parses without grammar filter."""
        repo = LogRepository(repo_with_logs)
        entries = list(repo.recent_parses(limit=None))
        assert len(entries) == TOTAL_PARSE_ENTRIES

    def test_empty_logs(self, tmp_path: Path) -> None:
        """Handle empty log files gracefully."""
        repo = tmp_path / "empty_repo"
        repo.mkdir()
        (repo / "logs").mkdir()
        (repo / "grammars").mkdir()
        (repo / "build").mkdir()

        log_repo = LogRepository(repo)
        assert list(log_repo.recent_builds()) == []
        assert list(log_repo.recent_parses()) == []
