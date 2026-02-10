from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[1]
BUILD_SCRIPT = PROJECT_ROOT / "scripts" / "build_grammar.sh"


def require_toolchain() -> None:
    missing = [tool for tool in ("tree-sitter", "gcc", "bash") if shutil.which(tool) is None]
    if missing:
        pytest.skip(f"Required tool(s) unavailable in PATH: {', '.join(missing)}")


@pytest.fixture
def minimal_grammar(tmp_path: Path) -> Path:
    """Create minimal test grammar."""
    require_toolchain()
    grammar_dir = tmp_path / "minimal"
    grammar_dir.mkdir()

    fixture = PROJECT_ROOT / "tests" / "fixtures" / "minimal_grammar" / "grammar.js"
    shutil.copy(fixture, grammar_dir / "grammar.js")

    subprocess.run(
        ["tree-sitter", "generate"],
        cwd=grammar_dir,
        check=True,
        capture_output=True,
        text=True,
    )

    return grammar_dir


@pytest.fixture
def scanner_grammar(tmp_path: Path) -> Path:
    """Create grammar with C scanner."""
    require_toolchain()
    grammar_dir = tmp_path / "scanner_test"
    grammar_dir.mkdir()
    (grammar_dir / "src").mkdir()

    fixture_root = PROJECT_ROOT / "tests" / "fixtures" / "scanner_grammar"
    shutil.copy(fixture_root / "grammar.js", grammar_dir / "grammar.js")
    shutil.copy(fixture_root / "src" / "scanner.c", grammar_dir / "src" / "scanner.c")

    subprocess.run(
        ["tree-sitter", "generate"],
        cwd=grammar_dir,
        check=True,
        capture_output=True,
        text=True,
    )

    return grammar_dir


class TestBuildScript:
    def test_minimal_grammar_build(self, minimal_grammar: Path, tmp_path: Path) -> None:
        """Build grammar without scanner."""
        output_so = tmp_path / "minimal.so"

        result = subprocess.run(
            ["bash", str(BUILD_SCRIPT), str(minimal_grammar), str(output_so)],
            capture_output=True,
            text=True,
            cwd=PROJECT_ROOT,
        )

        assert result.returncode == 0, f"Build failed: {result.stderr}"
        assert output_so.exists()
        assert "No scanner file found" in result.stderr
        assert "Build successful" in result.stderr

    def test_scanner_grammar_build(self, scanner_grammar: Path, tmp_path: Path) -> None:
        """Build grammar with C scanner."""
        output_so = tmp_path / "scanner_test.so"

        result = subprocess.run(
            ["bash", str(BUILD_SCRIPT), str(scanner_grammar), str(output_so)],
            capture_output=True,
            text=True,
            cwd=PROJECT_ROOT,
        )

        assert result.returncode == 0, f"Build failed: {result.stderr}"
        assert output_so.exists()
        assert "Using C scanner" in result.stderr
        assert "Build successful" in result.stderr

    def test_missing_parser_fails_gracefully(self, tmp_path: Path) -> None:
        """Error includes generation hint when parser.c is missing."""
        grammar_dir = tmp_path / "missing_parser"
        (grammar_dir / "src").mkdir(parents=True)

        output_so = tmp_path / "missing_parser.so"

        result = subprocess.run(
            ["bash", str(BUILD_SCRIPT), str(grammar_dir), str(output_so)],
            capture_output=True,
            text=True,
            cwd=PROJECT_ROOT,
        )

        assert result.returncode != 0
        assert f"Error: {grammar_dir}/src/parser.c not found" in result.stderr
        assert "Run 'tree-sitter generate'" in result.stderr

    def test_creates_output_directory(self, minimal_grammar: Path, tmp_path: Path) -> None:
        """Output directory is created automatically."""
        output_so = tmp_path / "nested" / "out" / "minimal.so"

        result = subprocess.run(
            ["bash", str(BUILD_SCRIPT), str(minimal_grammar), str(output_so)],
            capture_output=True,
            text=True,
            cwd=PROJECT_ROOT,
        )

        assert result.returncode == 0, f"Build failed: {result.stderr}"
        assert output_so.exists()

    def test_usage_error_when_args_missing(self) -> None:
        """Script exits non-zero with usage info when args are missing."""
        result = subprocess.run(
            ["bash", str(BUILD_SCRIPT)],
            capture_output=True,
            text=True,
            cwd=PROJECT_ROOT,
        )

        assert result.returncode != 0
        assert "Usage:" in result.stderr
