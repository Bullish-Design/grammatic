from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

import pytest

from grammatic.contracts import BuildRequest, DoctorRequest, GenerateRequest
from grammatic.workflows import handle_build, handle_doctor, handle_generate

PROJECT_ROOT = Path(__file__).resolve().parents[1]


def require_toolchain() -> None:
    """Skip tests if required tools are not available."""
    missing = [tool for tool in ("git", "tree-sitter", "gcc") if shutil.which(tool) is None]
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

    return repo


class TestGenerateWorkflow:
    """Test generate workflow."""

    def test_generate_creates_parser(self, test_repo: Path) -> None:
        """Generate creates parser.c in grammar source directory."""
        grammar_dir = test_repo / "grammars" / "test"
        grammar_dir.mkdir()

        # Create minimal grammar.js
        grammar_js = grammar_dir / "grammar.js"
        grammar_js.write_text(
            """
            module.exports = grammar({
                name: 'test',
                rules: {
                    source_file: $ => repeat($.line),
                    line: $ => /[^\\n]*\\n/
                }
            });
            """
        )

        result = handle_generate(GenerateRequest(grammar="test", repo_root=test_repo))

        assert result.status == "ok"
        assert (grammar_dir / "src" / "parser.c").exists()

    def test_generate_fails_without_grammar_js(self, test_repo: Path) -> None:
        """Generate fails when grammar.js is missing."""
        (test_repo / "grammars" / "missing").mkdir()

        with pytest.raises(Exception):
            handle_generate(GenerateRequest(grammar="missing", repo_root=test_repo))


class TestDoctorWorkflow:
    """Test doctor diagnostic workflow."""

    def test_doctor_validates_grammar_structure(self, test_repo: Path) -> None:
        """Doctor checks grammar structure and reports issues."""
        grammar_dir = test_repo / "grammars" / "incomplete"
        grammar_dir.mkdir()

        # Create empty grammar.js (invalid)
        (grammar_dir / "grammar.js").touch()

        result = handle_doctor(DoctorRequest(grammar="incomplete", repo_root=test_repo))

        # Doctor should report issues
        assert result.status == "error" or len(result.findings) > 0

    def test_doctor_checks_corpus_tests(self, test_repo: Path) -> None:
        """Doctor verifies corpus test presence."""
        grammar_dir = test_repo / "grammars" / "test"
        grammar_dir.mkdir()

        # Create minimal valid grammar
        (grammar_dir / "grammar.js").write_text(
            "module.exports = grammar({ name: 'test', rules: { source_file: $ => /.*/ } });"
        )

        # Generate and build
        handle_generate(GenerateRequest(grammar="test", repo_root=test_repo))
        handle_build(BuildRequest(grammar="test", repo_root=test_repo))

        # Create empty corpus directory
        (grammar_dir / "test" / "corpus").mkdir(parents=True)

        result = handle_doctor(DoctorRequest(grammar="test", repo_root=test_repo))

        # Should report missing or empty corpus
        assert len(result.findings) > 0 or result.status == "error"


class TestWorkspaceLayout:
    """Test workspace layout and path conventions."""

    def test_canonical_build_paths(self, test_repo: Path) -> None:
        """Verify canonical build output paths."""
        grammar_dir = test_repo / "grammars" / "mygrammar"
        grammar_dir.mkdir()

        (grammar_dir / "grammar.js").write_text(
            "module.exports = grammar({ name: 'mygrammar', rules: { source_file: $ => /.*/ } });"
        )

        handle_generate(GenerateRequest(grammar="mygrammar", repo_root=test_repo))
        result = handle_build(BuildRequest(grammar="mygrammar", repo_root=test_repo))

        # Verify canonical path: build/<grammar>/<grammar>.so
        expected_path = test_repo / "build" / "mygrammar" / "mygrammar.so"
        assert result.artifact_path == expected_path
        assert expected_path.exists()

    def test_parser_generated_in_grammar_src(self, test_repo: Path) -> None:
        """Verify parser.c is generated in grammar/src/, not build/."""
        grammar_dir = test_repo / "grammars" / "test"
        grammar_dir.mkdir()

        (grammar_dir / "grammar.js").write_text(
            "module.exports = grammar({ name: 'test', rules: { source_file: $ => /.*/ } });"
        )

        handle_generate(GenerateRequest(grammar="test", repo_root=test_repo))

        # Parser should be in grammar source dir
        assert (grammar_dir / "src" / "parser.c").exists()

        # Parser should NOT be in build dir
        assert not (test_repo / "build" / "test" / "parser.c").exists()
