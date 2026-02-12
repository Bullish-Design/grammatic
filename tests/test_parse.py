from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[1]


def require_toolchain() -> None:
    missing = [
        tool
        for tool in ("git", "just", "tree-sitter", "uv", "jq", "gcc")
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
    shutil.copy(PROJECT_ROOT / "scripts" / "just" / "path_checks.just", repo / "scripts" / "just" / "path_checks.just")
    shutil.copy(PROJECT_ROOT / "scripts" / "just" / "path_checks.py", repo / "scripts" / "just" / "path_checks.py")
    shutil.copy(PROJECT_ROOT / "src" / "grammatic" / "models.py", repo / "src" / "grammatic" / "models.py")
    shutil.copy(PROJECT_ROOT / "src" / "grammatic" / "__init__.py", repo / "src" / "grammatic" / "__init__.py")

    return repo


def setup_minimal_grammar(repo: Path, grammar_name: str = "minimal") -> Path:
    grammar_dir = repo / "grammars" / grammar_name
    grammar_dir.mkdir(parents=True, exist_ok=True)
    shutil.copy(PROJECT_ROOT / "tests" / "fixtures" / "minimal_grammar" / "grammar.js", grammar_dir / "grammar.js")

    subprocess.run(["git", "init"], check=True, capture_output=True, cwd=grammar_dir)
    subprocess.run(["git", "config", "user.name", "Test"], check=True, capture_output=True, cwd=grammar_dir)
    subprocess.run(["git", "config", "user.email", "test@test.com"], check=True, capture_output=True, cwd=grammar_dir)
    subprocess.run(["git", "add", "."], check=True, capture_output=True, cwd=grammar_dir)
    subprocess.run(["git", "commit", "-m", "Initial"], check=True, capture_output=True, cwd=grammar_dir)
    subprocess.run(
        ["git", "remote", "add", "origin", f"https://example.com/{grammar_name}"],
        check=True,
        capture_output=True,
        cwd=grammar_dir,
    )

    return grammar_dir


@pytest.fixture
def minimal_grammar_built(test_repo: Path) -> Path:
    subprocess.run(["just", "init"], check=True, capture_output=True, cwd=test_repo)
    setup_minimal_grammar(test_repo)
    subprocess.run(["just", "generate", "minimal"], check=True, capture_output=True, cwd=test_repo)
    subprocess.run(["just", "build", "minimal"], check=True, capture_output=True, cwd=test_repo)
    return test_repo


class TestParse:
    def test_parse_valid_file(self, minimal_grammar_built: Path) -> None:
        test_file = minimal_grammar_built / "test.txt"
        test_file.write_text("hello\nworld\n")

        result = subprocess.run(
            ["just", "parse", "minimal", str(test_file)],
            capture_output=True,
            text=True,
            check=True,
            cwd=minimal_grammar_built,
        )

        assert "Parse logged" in result.stdout
        assert (minimal_grammar_built / "logs" / "parses.jsonl").exists()

    def test_parse_logs_event(self, minimal_grammar_built: Path) -> None:
        test_file = minimal_grammar_built / "test.txt"
        test_file.write_text("line one\nline two\n")

        subprocess.run(
            ["just", "parse", "minimal", str(test_file)],
            check=True,
            capture_output=True,
            cwd=minimal_grammar_built,
        )

        with (minimal_grammar_built / "logs" / "parses.jsonl").open(encoding="utf-8") as handle:
            entry = json.loads(handle.read().strip().splitlines()[-1])

        assert entry["event_type"] == "parse"
        assert entry["grammar"] == "minimal"
        assert entry["node_count"] > 0
        assert entry["has_errors"] is False

    def test_parse_without_build(self, test_repo: Path) -> None:
        subprocess.run(["just", "init"], check=True, capture_output=True, cwd=test_repo)

        test_file = test_repo / "test.txt"
        test_file.write_text("test")

        result = subprocess.run(
            ["just", "parse", "nonexistent", str(test_file)],
            capture_output=True,
            text=True,
            cwd=test_repo,
        )

        assert result.returncode == 1
        assert "not found" in result.stderr.lower()
        assert "Parse logged" not in result.stdout
        assert not (test_repo / "logs" / "parses.jsonl").exists()

    def test_parse_missing_source_returns_nonzero_and_does_not_log(self, minimal_grammar_built: Path) -> None:
        missing_file = minimal_grammar_built / "missing.txt"

        result = subprocess.run(
            ["just", "parse", "minimal", str(missing_file)],
            capture_output=True,
            text=True,
            cwd=minimal_grammar_built,
        )

        assert result.returncode == 1
        assert "source file not found" in result.stderr
        assert "Parse logged" not in result.stdout
        assert not (minimal_grammar_built / "logs" / "parses.jsonl").exists()

    def test_parse_detects_errors_field(self, minimal_grammar_built: Path) -> None:
        test_file = minimal_grammar_built / "test.txt"
        test_file.write_text("valid line\n")

        subprocess.run(
            ["just", "parse", "minimal", str(test_file)],
            check=True,
            capture_output=True,
            cwd=minimal_grammar_built,
        )

        with (minimal_grammar_built / "logs" / "parses.jsonl").open(encoding="utf-8") as handle:
            entry = json.loads(handle.read().strip().splitlines()[-1])

        assert "has_errors" in entry
        assert isinstance(entry["has_errors"], bool)


class TestCorpusTests:
    def test_run_corpus_tests(self, test_repo: Path) -> None:
        subprocess.run(["just", "init"], check=True, capture_output=True, cwd=test_repo)
        grammar_dir = setup_minimal_grammar(test_repo)

        corpus_dir = grammar_dir / "test" / "corpus"
        corpus_dir.mkdir(parents=True)
        shutil.copy(
            PROJECT_ROOT / "tests" / "fixtures" / "minimal_grammar" / "test" / "corpus" / "basic.txt",
            corpus_dir / "basic.txt",
        )

        subprocess.run(["just", "generate", "minimal"], check=True, capture_output=True, cwd=test_repo)

        result = subprocess.run(
            ["just", "test-grammar", "minimal"],
            capture_output=True,
            text=True,
            check=True,
            cwd=test_repo,
        )

        assert result.returncode == 0

    def test_corpus_tests_missing(self, test_repo: Path) -> None:
        subprocess.run(["just", "init"], check=True, capture_output=True, cwd=test_repo)
        (test_repo / "grammars" / "nocorpus").mkdir(parents=True)

        result = subprocess.run(
            ["just", "test-grammar", "nocorpus"],
            capture_output=True,
            text=True,
            cwd=test_repo,
        )

        assert result.returncode == 1
        assert "No corpus tests" in result.stderr


class TestFullCycle:
    def test_full_test_target(self, test_repo: Path) -> None:
        subprocess.run(["just", "init"], check=True, capture_output=True, cwd=test_repo)
        setup_minimal_grammar(test_repo)
        subprocess.run(["just", "generate", "minimal"], check=True, capture_output=True, cwd=test_repo)

        fixture = test_repo / "tests" / "fixtures" / "sample_minimal.txt"
        fixture.write_text("test line\n")

        subprocess.run(
            ["just", "test", "minimal"],
            capture_output=True,
            text=True,
            check=True,
            cwd=test_repo,
        )

        assert (test_repo / "build" / "minimal" / "minimal.so").exists()
        assert (test_repo / "logs" / "builds.jsonl").exists()
        assert (test_repo / "logs" / "parses.jsonl").exists()
