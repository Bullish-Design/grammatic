from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

import pytest

from grammatic.contracts import BuildRequest, GenerateRequest
from grammatic.errors import ArtifactMissingError
from grammatic.workflows import handle_build, handle_generate

PROJECT_ROOT = Path(__file__).resolve().parents[1]


def require_toolchain() -> None:
    """Skip tests if required tools are not available."""
    missing = [tool for tool in ("tree-sitter", "gcc") if shutil.which(tool) is None]
    if missing:
        pytest.skip(f"Required tool(s) unavailable in PATH: {', '.join(missing)}")


@pytest.fixture
def test_repo(tmp_path: Path) -> Path:
    """Create a test repository structure."""
    require_toolchain()

    repo = tmp_path / "test_repo"
    (repo / "grammars").mkdir(parents=True)
    (repo / "build").mkdir(parents=True)
    (repo / "logs").mkdir(parents=True)
    (repo / "scripts").mkdir(parents=True)

    return repo


def setup_minimal_grammar(repo: Path) -> Path:
    """Set up a minimal test grammar."""
    grammar_dir = repo / "grammars" / "minimal"
    grammar_dir.mkdir(parents=True)

    fixture = PROJECT_ROOT / "tests" / "fixtures" / "minimal_grammar" / "grammar.js"
    shutil.copy(fixture, grammar_dir / "grammar.js")

    return grammar_dir


def setup_scanner_grammar(repo: Path, scanner_type: str) -> Path:
    """Set up a grammar with scanner (C or C++)."""
    grammar_dir = repo / "grammars" / "scanner_test"
    grammar_dir.mkdir(parents=True)
    (grammar_dir / "src").mkdir()

    fixture_root = PROJECT_ROOT / "tests" / "fixtures" / "scanner_grammar"
    shutil.copy(fixture_root / "grammar.js", grammar_dir / "grammar.js")

    if scanner_type == "c":
        shutil.copy(fixture_root / "src" / "scanner.c", grammar_dir / "src" / "scanner.c")
    elif scanner_type == "cpp":
        shutil.copy(fixture_root / "src" / "scanner.c", grammar_dir / "src" / "scanner.cc")

    return grammar_dir


class TestBuildWorkflow:
    """Test build workflow using Python API directly."""

    def test_minimal_grammar_build(self, test_repo: Path) -> None:
        """Build a minimal grammar without scanner."""
        setup_minimal_grammar(test_repo)

        # Generate parser first
        handle_generate(GenerateRequest(grammar="minimal", repo_root=test_repo))

        # Build the grammar
        result = handle_build(BuildRequest(grammar="minimal", repo_root=test_repo))

        assert result.status == "ok"
        assert result.artifact_path.exists()
        assert result.artifact_path == test_repo / "build" / "minimal" / "minimal.so"
        assert result.compiler in ("gcc", "g++")

    def test_scanner_grammar_build_c(self, test_repo: Path) -> None:
        """Build grammar with C scanner."""
        setup_scanner_grammar(test_repo, "c")

        handle_generate(GenerateRequest(grammar="scanner_test", repo_root=test_repo))
        result = handle_build(BuildRequest(grammar="scanner_test", repo_root=test_repo))

        assert result.status == "ok"
        assert result.artifact_path.exists()
        assert result.compiler == "gcc"

    def test_scanner_grammar_build_cpp(self, test_repo: Path) -> None:
        """Build grammar with C++ scanner."""
        setup_scanner_grammar(test_repo, "cpp")

        handle_generate(GenerateRequest(grammar="scanner_test", repo_root=test_repo))
        result = handle_build(BuildRequest(grammar="scanner_test", repo_root=test_repo))

        assert result.status == "ok"
        assert result.artifact_path.exists()
        assert result.compiler == "g++"

    def test_missing_parser_fails_gracefully(self, test_repo: Path) -> None:
        """Build fails with clear error when parser.c is missing."""
        grammar_dir = test_repo / "grammars" / "missing_parser"
        (grammar_dir / "src").mkdir(parents=True)

        with pytest.raises(ArtifactMissingError) as exc_info:
            handle_build(BuildRequest(grammar="missing_parser", repo_root=test_repo))

        error_message = str(exc_info.value)
        assert "parser.c" in error_message
        assert "generate" in error_message.lower()

    def test_creates_output_directory(self, test_repo: Path) -> None:
        """Build creates output directory automatically."""
        setup_minimal_grammar(test_repo)

        handle_generate(GenerateRequest(grammar="minimal", repo_root=test_repo))

        # Remove build directory to test auto-creation
        build_dir = test_repo / "build"
        if build_dir.exists():
            shutil.rmtree(build_dir)

        result = handle_build(BuildRequest(grammar="minimal", repo_root=test_repo))

        assert result.status == "ok"
        assert result.artifact_path.exists()
        assert result.artifact_path.parent.exists()

    def test_build_creates_logs(self, test_repo: Path) -> None:
        """Build operations create log entries."""
        setup_minimal_grammar(test_repo)

        handle_generate(GenerateRequest(grammar="minimal", repo_root=test_repo))
        handle_build(BuildRequest(grammar="minimal", repo_root=test_repo))

        builds_log = test_repo / "logs" / "builds.jsonl"
        assert builds_log.exists()

        import json

        with builds_log.open(encoding="utf-8") as handle:
            entry = json.loads(handle.read().strip().splitlines()[-1])

        assert entry["event_type"] == "build"
        assert entry["grammar"] == "minimal"
        assert entry["status"] == "success"
        assert entry["duration_ms"] > 0

    def test_build_result_contains_metadata(self, test_repo: Path) -> None:
        """Build result contains compiler and duration metadata."""
        setup_minimal_grammar(test_repo)

        handle_generate(GenerateRequest(grammar="minimal", repo_root=test_repo))
        result = handle_build(BuildRequest(grammar="minimal", repo_root=test_repo))

        assert result.compiler in ("gcc", "g++")
        assert result.duration_ms > 0
        assert isinstance(result.duration_ms, int)
        assert result.grammar == "minimal"
