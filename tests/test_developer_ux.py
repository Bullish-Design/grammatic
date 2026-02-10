from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[1]


def require_toolchain() -> None:
    missing = [
        tool
        for tool in ("git", "just", "tree-sitter", "uv", "jq", "gcc", "python")
        if shutil.which(tool) is None
    ]
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
    (repo / "tests" / "fixtures").mkdir(parents=True)

    shutil.copy(PROJECT_ROOT / "justfile", repo / "justfile")
    shutil.copy(PROJECT_ROOT / "scripts" / "build_grammar.py", repo / "scripts" / "build_grammar.py")
    shutil.copy(PROJECT_ROOT / "scripts" / "log_writer.py", repo / "scripts" / "log_writer.py")
    shutil.copy(PROJECT_ROOT / "scripts" / "query_logs.py", repo / "scripts" / "query_logs.py")
    shutil.copy(PROJECT_ROOT / "scripts" / "grammar_doctor.py", repo / "scripts" / "grammar_doctor.py")
    shutil.copy(PROJECT_ROOT / "scripts" / "just" / "path_checks.just", repo / "scripts" / "just" / "path_checks.just")
    shutil.copy(PROJECT_ROOT / "scripts" / "just" / "path_checks.py", repo / "scripts" / "just" / "path_checks.py")
    shutil.copy(PROJECT_ROOT / "src" / "grammatic" / "models.py", repo / "src" / "grammatic" / "models.py")
    shutil.copy(PROJECT_ROOT / "src" / "grammatic" / "__init__.py", repo / "src" / "grammatic" / "__init__.py")

    return repo


class TestNewGrammar:
    def test_creates_template(self, test_repo: Path) -> None:
        subprocess.run(["just", "init"], check=True, capture_output=True, cwd=test_repo)

        subprocess.run(
            ["just", "new-grammar", "mytest"],
            capture_output=True,
            text=True,
            check=True,
            cwd=test_repo,
        )

        assert (test_repo / "grammars" / "mytest" / "grammar.js").exists()
        assert (test_repo / "grammars" / "mytest" / "test" / "corpus" / "basic.txt").exists()
        assert (test_repo / "grammars" / "mytest" / "README.md").exists()

    def test_prevents_duplicate_grammar(self, test_repo: Path) -> None:
        subprocess.run(["just", "init"], check=True, capture_output=True, cwd=test_repo)
        (test_repo / "grammars" / "existing").mkdir(parents=True)

        result = subprocess.run(
            ["just", "new-grammar", "existing"],
            capture_output=True,
            text=True,
            cwd=test_repo,
        )

        assert result.returncode == 1
        assert "already exists" in result.stderr


class TestListGrammars:
    def test_lists_grammars(self, test_repo: Path) -> None:
        subprocess.run(["just", "init"], check=True, capture_output=True, cwd=test_repo)

        (test_repo / "grammars" / "test1").mkdir(parents=True)
        (test_repo / "grammars" / "test2").mkdir(parents=True)
        (test_repo / "build" / "test1" ).mkdir(parents=True)
        (test_repo / "build" / "test1" / "test1.so").touch()

        result = subprocess.run(
            ["just", "list-grammars"],
            capture_output=True,
            text=True,
            check=True,
            cwd=test_repo,
        )

        assert "test1 (built)" in result.stdout
        assert "test2 (not built)" in result.stdout


class TestGrammarInfo:
    def test_shows_info(self, test_repo: Path) -> None:
        subprocess.run(["just", "init"], check=True, capture_output=True, cwd=test_repo)

        grammar_dir = test_repo / "grammars" / "test"
        grammar_dir.mkdir(parents=True)
        (grammar_dir / "grammar.js").write_text(
            "module.exports = grammar({ name: 'test', rules: { source_file: $ => /.*/ } });"
        )
        (grammar_dir / "src").mkdir()
        (grammar_dir / "src" / "parser.c").touch()
        (test_repo / "build" / "test").mkdir(parents=True)
        (test_repo / "build" / "test" / "test.so").touch()

        result = subprocess.run(
            ["just", "info", "test"],
            capture_output=True,
            text=True,
            check=True,
            cwd=test_repo,
        )

        assert "Grammar: test" in result.stdout
        assert "Grammar file: ✓" in result.stdout
        assert "Parser generated: ✓" in result.stdout
        assert "Built: ✓" in result.stdout


class TestGrammarDoctor:
    def test_detects_issues(self, test_repo: Path) -> None:
        subprocess.run(["just", "init"], check=True, capture_output=True, cwd=test_repo)

        grammar_dir = test_repo / "grammars" / "broken"
        grammar_dir.mkdir(parents=True)
        (grammar_dir / "grammar.js").touch()

        result = subprocess.run(
            ["just", "doctor", "broken"],
            capture_output=True,
            text=True,
            cwd=test_repo,
        )

        assert result.returncode == 1
        assert "Issues found" in result.stdout


class TestHelp:
    def test_help_target(self, test_repo: Path) -> None:
        subprocess.run(["just", "init"], check=True, capture_output=True, cwd=test_repo)

        result = subprocess.run(
            ["just", "help"],
            capture_output=True,
            text=True,
            check=True,
            cwd=test_repo,
        )

        assert result.returncode == 0
        assert len(result.stdout) > 0
