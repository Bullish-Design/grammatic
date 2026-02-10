from __future__ import annotations

import json
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[1]


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
        assert len(lines) == 3

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

    def test_query_parses(self, repo_with_logs: Path) -> None:
        result = subprocess.run(
            ["just", "query-parses", "10"],
            capture_output=True,
            text=True,
            check=True,
            cwd=repo_with_logs,
        )

        lines = result.stdout.strip().split("\n")
        assert len(lines) == 2

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
