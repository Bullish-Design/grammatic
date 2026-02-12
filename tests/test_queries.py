from __future__ import annotations

import json
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SPECIAL_GRAMMARS = ['quote"name', 'dollar$name', 'bracket[name]']
BASE_BUILD_ENTRIES = 4
BASE_PARSE_ENTRIES = 3
TOTAL_BUILD_ENTRIES = BASE_BUILD_ENTRIES + len(SPECIAL_GRAMMARS)
TOTAL_PARSE_ENTRIES = BASE_PARSE_ENTRIES + len(SPECIAL_GRAMMARS)


def require_toolchain() -> None:
    missing = [tool for tool in ("git", "just", "jq", "tar") if shutil.which(tool) is None]
    if missing:
        pytest.skip(f"Required tool(s) unavailable in PATH: {', '.join(missing)}")


@pytest.fixture
def test_repo(tmp_path: Path) -> Path:
    require_toolchain()

    repo = tmp_path / "test_repo"
    repo.mkdir()

    subprocess.run(["git", "init"], check=True, capture_output=True, cwd=repo)
    subprocess.run(["git", "config", "user.name", "Test"], check=True, capture_output=True, cwd=repo)
    subprocess.run(["git", "config", "user.email", "test@test.com"], check=True, capture_output=True, cwd=repo)

    (repo / "scripts" / "just").mkdir(parents=True)
    (repo / "src" / "grammatic").mkdir(parents=True)

    shutil.copy(PROJECT_ROOT / "justfile", repo / "justfile")
    shutil.copy(PROJECT_ROOT / "scripts" / "query_logs.py", repo / "scripts" / "query_logs.py")
    shutil.copy(PROJECT_ROOT / "scripts" / "just" / "path_checks.just", repo / "scripts" / "just" / "path_checks.just")
    shutil.copy(PROJECT_ROOT / "scripts" / "just" / "path_checks.py", repo / "scripts" / "just" / "path_checks.py")
    shutil.copy(PROJECT_ROOT / "src" / "grammatic" / "models.py", repo / "src" / "grammatic" / "models.py")
    shutil.copy(PROJECT_ROOT / "src" / "grammatic" / "__init__.py", repo / "src" / "grammatic" / "__init__.py")

    return repo


@pytest.fixture
def repo_with_logs(test_repo: Path) -> Path:
    subprocess.run(["just", "init"], check=True, capture_output=True, cwd=test_repo)

    builds_log = test_repo / "logs" / "builds.jsonl"
    builds_log.write_text(
        "\n".join(
            [
                json.dumps(
                    {
                        "event_type": "build",
                        "grammar": "test",
                        "build_success": True,
                        "build_time_ms": 100,
                        "timestamp": "2026-01-01T10:00:00",
                    }
                ),
                json.dumps(
                    {
                        "event_type": "build",
                        "grammar": "test",
                        "build_success": False,
                        "build_time_ms": 150,
                        "timestamp": "2026-01-01T11:00:00",
                    }
                ),
                json.dumps(
                    {
                        "event_type": "build",
                        "grammar": "other",
                        "build_success": True,
                        "build_time_ms": 200,
                        "timestamp": "2026-01-01T12:00:00",
                    }
                ),
                json.dumps(
                    {
                        "event_type": "build",
                        "grammar": 'odd"name$[]',
                        "build_success": True,
                        "build_time_ms": 90,
                        "timestamp": "2026-01-01T12:30:00",
                    }
                ),
                *[
                    json.dumps(
                        {
                            "event_type": "build",
                            "grammar": grammar,
                            "build_success": True,
                            "build_time_ms": 95,
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

    parses_log = test_repo / "logs" / "parses.jsonl"
    parses_log.write_text(
        "\n".join(
            [
                json.dumps(
                    {
                        "event_type": "parse",
                        "grammar": "test",
                        "grammar_version": "abc123",
                        "has_errors": False,
                        "parse_time_ms": 10,
                        "timestamp": "2026-01-01T13:00:00",
                    }
                ),
                json.dumps(
                    {
                        "event_type": "parse",
                        "grammar": "test",
                        "grammar_version": "def456",
                        "has_errors": True,
                        "parse_time_ms": 20,
                        "timestamp": "2026-01-01T14:00:00",
                    }
                ),
                json.dumps(
                    {
                        "event_type": "parse",
                        "grammar": 'odd"name$[]',
                        "grammar_version": "ghi789",
                        "has_errors": False,
                        "parse_time_ms": 7,
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
                            "parse_time_ms": 8,
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

    return test_repo


class TestLogQueries:
    def test_query_builds(self, repo_with_logs: Path) -> None:
        result = subprocess.run(
            ["just", "query-builds", "10"],
            capture_output=True,
            text=True,
            check=True,
            cwd=repo_with_logs,
        )
        lines = result.stdout.strip().split("\n")
        assert len(lines) == TOTAL_BUILD_ENTRIES

    def test_query_builds_for_grammar(self, repo_with_logs: Path) -> None:
        result = subprocess.run(
            ["just", "query-builds-for", "test"],
            capture_output=True,
            text=True,
            check=True,
            cwd=repo_with_logs,
        )

        lines = result.stdout.strip().split("\n")
        assert len(lines) == 2
        assert all('"grammar":"test"' in line for line in lines)


    @pytest.mark.parametrize("grammar", ['odd"name$[]', *SPECIAL_GRAMMARS])
    def test_query_builds_for_grammar_with_special_chars(self, repo_with_logs: Path, grammar: str) -> None:
        result = subprocess.run(
            ["just", "query-builds-for", grammar],
            capture_output=True,
            text=True,
            check=True,
            cwd=repo_with_logs,
        )

        lines = result.stdout.strip().split("\n")
        assert len(lines) == 1
        entry = json.loads(lines[0])
        assert entry["grammar"] == grammar

    @pytest.mark.parametrize("grammar", ['odd"name$[]', *SPECIAL_GRAMMARS])
    def test_query_parses_for_grammar_with_special_chars(self, repo_with_logs: Path, grammar: str) -> None:
        result = subprocess.run(
            ["just", "query-parses-for", grammar],
            capture_output=True,
            text=True,
            check=True,
            cwd=repo_with_logs,
        )

        lines = result.stdout.strip().split("\n")
        assert len(lines) == 1
        entry = json.loads(lines[0])
        assert entry["grammar"] == grammar

    @pytest.mark.parametrize("grammar", ['odd"name$[]', *SPECIAL_GRAMMARS])
    def test_build_success_rate_with_special_chars(self, repo_with_logs: Path, grammar: str) -> None:
        result = subprocess.run(
            ["just", "build-success-rate", grammar],
            capture_output=True,
            text=True,
            check=True,
            cwd=repo_with_logs,
        )

        rates = json.loads(result.stdout)
        assert rates == [{"success": True, "count": 1}]

    def test_query_parses(self, repo_with_logs: Path) -> None:
        result = subprocess.run(
            ["just", "query-parses", "10"],
            capture_output=True,
            text=True,
            check=True,
            cwd=repo_with_logs,
        )

        lines = result.stdout.strip().split("\n")
        assert len(lines) == TOTAL_PARSE_ENTRIES

    def test_query_failures(self, repo_with_logs: Path) -> None:
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

    def test_build_success_rate(self, repo_with_logs: Path) -> None:
        result = subprocess.run(
            ["just", "build-success-rate", "test"],
            capture_output=True,
            text=True,
            check=True,
            cwd=repo_with_logs,
        )

        rates = json.loads(result.stdout)
        assert len(rates) == 2

    def test_avg_parse_time(self, repo_with_logs: Path) -> None:
        result = subprocess.run(
            ["just", "avg-parse-time", "test"],
            capture_output=True,
            text=True,
            check=True,
            cwd=repo_with_logs,
        )

        avg = float(result.stdout.strip())
        assert avg == 15.0


class TestLogValidation:
    def test_validate_valid_logs(self, repo_with_logs: Path) -> None:
        result = subprocess.run(
            ["just", "validate-logs"],
            capture_output=True,
            text=True,
            check=True,
            cwd=repo_with_logs,
        )

        assert "validation complete" in result.stdout.lower()

    def test_validate_missing_logs(self, test_repo: Path) -> None:
        subprocess.run(["just", "init"], check=True, capture_output=True, cwd=test_repo)

        result = subprocess.run(
            ["just", "validate-logs"],
            capture_output=True,
            text=True,
            check=True,
            cwd=test_repo,
        )

        assert result.returncode == 0

    def test_validate_invalid_builds_log_fails(self, repo_with_logs: Path) -> None:
        builds_log = repo_with_logs / "logs" / "builds.jsonl"
        builds_log.write_text('{"event_type":"build"}\n{invalid-json}\n', encoding="utf-8")

        result = subprocess.run(
            ["just", "validate-logs"],
            capture_output=True,
            text=True,
            cwd=repo_with_logs,
        )

        assert result.returncode != 0
        combined_output = f"{result.stdout}\n{result.stderr}".lower()
        assert "builds.jsonl has invalid json" in combined_output
        assert "log validation failed" in combined_output


class TestLogExport:
    def test_export_logs(self, repo_with_logs: Path, tmp_path: Path) -> None:
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
        assert len(list(output_dir.glob("grammatic-logs-*.tar.gz"))) == 1

    def test_exported_tarball_contents(self, repo_with_logs: Path, tmp_path: Path) -> None:
        output_dir = tmp_path / "exports"
        output_dir.mkdir()

        subprocess.run(
            ["just", "export-logs", str(output_dir)],
            check=True,
            capture_output=True,
            cwd=repo_with_logs,
        )

        tarball = list(output_dir.glob("grammatic-logs-*.tar.gz"))[0]
        extract_dir = tmp_path / "extracted"
        extract_dir.mkdir()
        subprocess.run(["tar", "xzf", str(tarball), "-C", str(extract_dir)], check=True)

        assert (extract_dir / "logs" / "builds.jsonl").exists()
        assert (extract_dir / "logs" / "parses.jsonl").exists()


class TestComplexQueries:
    def test_query_logs_summary(self, repo_with_logs: Path) -> None:
        result = subprocess.run(
            [sys.executable, "scripts/query_logs.py", "summary"],
            capture_output=True,
            text=True,
            check=True,
            cwd=repo_with_logs,
        )

        assert "Total builds" in result.stdout
        assert "Total parses" in result.stdout
        assert "success rate" in result.stdout

    def test_query_logs_grammar_stats(self, repo_with_logs: Path) -> None:
        result = subprocess.run(
            [sys.executable, "scripts/query_logs.py", "grammar-stats"],
            capture_output=True,
            text=True,
            check=True,
            cwd=repo_with_logs,
        )

        assert "test:" in result.stdout
        assert "other:" in result.stdout
