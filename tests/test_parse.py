from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path

import pytest

from grammatic.contracts import ParseRequest, TestGrammarRequest
from grammatic.errors import ValidationError
from grammatic.workflows import handle_parse, handle_test_grammar

PROJECT_ROOT = Path(__file__).resolve().parents[1]


def require_toolchain() -> None:
    """Skip tests if required tools are not available."""
    missing = [tool for tool in ("tree-sitter", "gcc") if shutil.which(tool) is None]
    if missing:
        pytest.skip(f"Required tool(s) unavailable in PATH: {', '.join(missing)}")


def setup_minimal_grammar(repo: Path, grammar_name: str = "minimal") -> Path:
    """Set up a minimal test grammar."""
    grammar_dir = repo / "grammars" / grammar_name
    grammar_dir.mkdir(parents=True, exist_ok=True)
    (grammar_dir / "src").mkdir(exist_ok=True)
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
def test_repo(tmp_path: Path) -> Path:
    """Create a test repository structure."""
    require_toolchain()

    repo = tmp_path / "test_repo"
    (repo / "grammars").mkdir(parents=True)
    (repo / "build").mkdir(parents=True)
    (repo / "logs").mkdir(parents=True)
    (repo / "scripts").mkdir(parents=True)

    return repo


@pytest.fixture
def minimal_grammar_built(test_repo: Path) -> Path:
    """Create and build a minimal grammar for testing."""
    from grammatic.contracts import BuildRequest, GenerateRequest
    from grammatic.workflows import handle_build, handle_generate

    setup_minimal_grammar(test_repo)

    # Generate parser
    handle_generate(GenerateRequest(grammar="minimal", repo_root=test_repo))

    # Build grammar
    handle_build(BuildRequest(grammar="minimal", repo_root=test_repo))

    return test_repo


class TestParse:
    """Test parse workflow using Python API directly."""

    def test_parse_valid_file(self, minimal_grammar_built: Path) -> None:
        """Parse a valid source file."""
        test_file = minimal_grammar_built / "test.txt"
        test_file.write_text("hello\nworld\n")

        result = handle_parse(ParseRequest(grammar="minimal", repo_root=minimal_grammar_built, source=test_file))

        assert result.status == "ok"
        assert result.grammar == "minimal"
        assert result.has_errors is False
        assert result.node_count > 0
        assert (minimal_grammar_built / "logs" / "parses.jsonl").exists()

    def test_parse_logs_event(self, minimal_grammar_built: Path) -> None:
        """Verify parse events are logged correctly."""
        test_file = minimal_grammar_built / "test.txt"
        test_file.write_text("line one\nline two\n")

        handle_parse(ParseRequest(grammar="minimal", repo_root=minimal_grammar_built, source=test_file))

        with (minimal_grammar_built / "logs" / "parses.jsonl").open(encoding="utf-8") as handle:
            entry = json.loads(handle.read().strip().splitlines()[-1])

        assert entry["event_type"] == "parse"
        assert entry["grammar"] == "minimal"
        assert entry["node_count"] > 0
        assert entry["has_errors"] is False

    def test_parse_without_build(self, test_repo: Path) -> None:
        """Parse fails gracefully when grammar is not built."""
        test_file = test_repo / "test.txt"
        test_file.write_text("test")

        with pytest.raises(Exception) as exc_info:
            handle_parse(ParseRequest(grammar="nonexistent", repo_root=test_repo, source=test_file))

        assert "not found" in str(exc_info.value).lower() or "nonexistent" in str(exc_info.value).lower()

    def test_parse_missing_source_returns_error(self, minimal_grammar_built: Path) -> None:
        """Parse fails when source file is missing."""
        missing_file = minimal_grammar_built / "missing.txt"

        with pytest.raises(ValidationError) as exc_info:
            handle_parse(ParseRequest(grammar="minimal", repo_root=minimal_grammar_built, source=missing_file))

        assert "source file not found" in str(exc_info.value).lower()

    def test_parse_detects_errors_field(self, minimal_grammar_built: Path) -> None:
        """Verify has_errors field is populated in parse results."""
        test_file = minimal_grammar_built / "test.txt"
        test_file.write_text("valid line\n")

        result = handle_parse(ParseRequest(grammar="minimal", repo_root=minimal_grammar_built, source=test_file))

        assert hasattr(result, "has_errors")
        assert isinstance(result.has_errors, bool)


    def test_parse_uses_scope_and_xml_flag(self, minimal_grammar_built: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """Parse invokes tree-sitter with scope and XML output flag."""
        test_file = minimal_grammar_built / "test.txt"
        test_file.write_text("hello\n")

        captured: dict[str, list[str]] = {}

        def fake_run_checked(cmd: list[str], cwd: Path | None = None, *, message: str | None = None) -> subprocess.CompletedProcess[str]:
            captured["cmd"] = cmd
            captured["cwd"] = [str(cwd)] if cwd is not None else []
            payload = "<source_file><line /></source_file>"
            return subprocess.CompletedProcess(cmd, 0, stdout=payload, stderr="")

        monkeypatch.setattr("grammatic.workflows.parse.ensure_tree_sitter_parse_support", lambda: "-x")
        monkeypatch.setattr("grammatic.workflows.parse.run_checked", fake_run_checked)

        result = handle_parse(ParseRequest(grammar="minimal", repo_root=minimal_grammar_built, source=test_file))

        assert result.status == "ok"
        assert captured["cmd"] == [
            "tree-sitter",
            "parse",
            "--scope",
            "minimal",
            "-x",
            str(test_file.resolve()),
        ]
        assert captured["cwd"] == [str((minimal_grammar_built / "grammars" / "minimal").resolve())]

    def test_parse_output_structure(self, minimal_grammar_built: Path) -> None:
        """Verify parse output has expected structure."""
        test_file = minimal_grammar_built / "test.txt"
        test_file.write_text("content\n")

        result = handle_parse(ParseRequest(grammar="minimal", repo_root=minimal_grammar_built, source=test_file))

        assert result.parse_output is not None
        assert isinstance(result.parse_output, dict)
        assert "root_node" in result.parse_output
        assert isinstance(result.parse_output["root_node"], dict)


class TestCorpusTests:
    """Test grammar corpus test execution."""

    def test_run_corpus_tests(self, test_repo: Path) -> None:
        """Run corpus tests for a grammar with test corpus."""
        from grammatic.contracts import BuildRequest, GenerateRequest
        from grammatic.workflows import handle_build, handle_generate

        grammar_dir = setup_minimal_grammar(test_repo)

        corpus_dir = grammar_dir / "test" / "corpus"
        corpus_dir.mkdir(parents=True)
        shutil.copy(
            PROJECT_ROOT / "tests" / "fixtures" / "minimal_grammar" / "test" / "corpus" / "basic.txt",
            corpus_dir / "basic.txt",
        )

        handle_generate(GenerateRequest(grammar="minimal", repo_root=test_repo))
        handle_build(BuildRequest(grammar="minimal", repo_root=test_repo))

        result = handle_test_grammar(TestGrammarRequest(grammar="minimal", repo_root=test_repo))

        assert result.status == "ok"

    def test_corpus_tests_missing(self, test_repo: Path) -> None:
        """Test-grammar fails when corpus is missing."""
        (test_repo / "grammars" / "nocorpus").mkdir(parents=True)

        with pytest.raises(Exception) as exc_info:
            handle_test_grammar(TestGrammarRequest(grammar="nocorpus", repo_root=test_repo))

        assert "corpus" in str(exc_info.value).lower()


class TestParseMetrics:
    """Test parse-related metrics and diagnostics."""

    def test_parse_duration_recorded(self, minimal_grammar_built: Path) -> None:
        """Verify parse duration is recorded."""
        test_file = minimal_grammar_built / "test.txt"
        test_file.write_text("test content\n")

        result = handle_parse(ParseRequest(grammar="minimal", repo_root=minimal_grammar_built, source=test_file))

        assert result.duration_ms > 0
        assert isinstance(result.duration_ms, int)

    def test_parse_node_count(self, minimal_grammar_built: Path) -> None:
        """Verify node count is calculated."""
        test_file = minimal_grammar_built / "test.txt"
        test_file.write_text("line1\nline2\nline3\n")

        result = handle_parse(ParseRequest(grammar="minimal", repo_root=minimal_grammar_built, source=test_file))

        assert result.node_count > 0
        assert isinstance(result.node_count, int)


class TestParseCapabilityCheck:
    """Test tree-sitter parse capability detection."""

    def test_supports_xml_flag(self, monkeypatch: pytest.MonkeyPatch) -> None:
        from grammatic import preflight

        def fake_run(cmd: list[str], cwd: Path | None = None) -> subprocess.CompletedProcess[str]:
            return subprocess.CompletedProcess(
                cmd,
                0,
                stdout="-x\n--xml\n",
                stderr="",
            )

        monkeypatch.setattr(preflight, "run", fake_run)

        assert preflight.ensure_tree_sitter_parse_support() == "-x"

    def test_errors_when_xml_parse_flag_missing(self, monkeypatch: pytest.MonkeyPatch) -> None:
        from grammatic import preflight

        def fake_run(cmd: list[str], cwd: Path | None = None) -> subprocess.CompletedProcess[str]:
            return subprocess.CompletedProcess(cmd, 0, stdout="--scope\n", stderr="")

        monkeypatch.setattr(preflight, "run", fake_run)

        with pytest.raises(ValidationError) as exc_info:
            preflight.ensure_tree_sitter_parse_support()

        assert "--xml" in str(exc_info.value)
