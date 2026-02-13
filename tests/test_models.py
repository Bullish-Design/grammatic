from __future__ import annotations

from datetime import datetime
from pathlib import Path

import pytest
from pydantic import ValidationError

from grammatic.models import (
    BuildLogEntry,
    BuildRequest,
    BuildResult,
    CommandExecutionMetadata,
    Diagnostic,
    DoctorRequest,
    DoctorResult,
    GenerateRequest,
    GenerateResult,
    GrammarMetadata,
    ParseLogEntry,
    ParseRequest,
    ParseResult,
    TestGrammarRequest,
    TestGrammarResult,
    WorkflowPaths,
)


def _make_repo_layout(tmp_path: Path) -> Path:
    (tmp_path / "grammars").mkdir(parents=True, exist_ok=True)
    (tmp_path / "scripts").mkdir(parents=True, exist_ok=True)
    (tmp_path / "build").mkdir(parents=True, exist_ok=True)
    (tmp_path / "logs").mkdir(parents=True, exist_ok=True)
    return tmp_path


def _make_grammar(tmp_path: Path, grammar: str) -> Path:
    grammar_dir = tmp_path / "grammars" / grammar
    (grammar_dir / "src").mkdir(parents=True, exist_ok=True)
    (grammar_dir / "grammar.js").write_text("module.exports = grammar({name: 'toy', rules: {}});")
    return grammar_dir


class TestBuildLogEntry:
    def test_valid_construction(self) -> None:
        entry = BuildLogEntry(
            timestamp=datetime.now(),
            grammar="python",
            commit="abc123",
            repo_url="https://github.com/tree-sitter/tree-sitter-python",
            so_path=Path("build/python.so"),
            status="success",
            duration_ms=1234,
            compiler="gcc",
            tree_sitter_version="0.21.0",
        )

        assert entry.event_type == "build"
        assert entry.grammar == "python"

    def test_invalid_compiler_raises_validation_error(self) -> None:
        with pytest.raises(ValidationError):
            BuildLogEntry(
                timestamp=datetime.now(),
                grammar="python",
                commit="abc123",
                repo_url="https://github.com/tree-sitter/tree-sitter-python",
                so_path=Path("build/python.so"),
                status="success",
                duration_ms=1234,
                compiler="clang",
                tree_sitter_version="0.21.0",
            )


class TestParseLogEntry:
    def test_valid_construction(self) -> None:
        entry = ParseLogEntry(
            timestamp=datetime.now(),
            grammar="python",
            grammar_version="abc123",
            source_file=Path("tests/fixtures/sample.py"),
            node_count=42,
            has_errors=False,
            status="success",
            duration_ms=12,
            root_node_type="module",
        )

        assert entry.event_type == "parse"
        assert entry.has_errors is False


class TestGrammarMetadata:
    def test_no_build_yet_case(self) -> None:
        metadata = GrammarMetadata(
            name="python",
            submodule_path=Path("grammars/python"),
            current_commit="abc123",
            remote_url="https://github.com/tree-sitter/tree-sitter-python",
            last_build_timestamp=None,
            so_exists=False,
        )

        assert metadata.last_build_timestamp is None
        assert metadata.so_exists is False


class TestWorkflowContracts:
    def test_workflow_paths_resolves_canonical_paths(self, tmp_path: Path) -> None:
        repo_root = _make_repo_layout(tmp_path)
        _make_grammar(repo_root, "toy")

        paths = WorkflowPaths(repo_root=repo_root, grammar="toy")

        assert paths.grammar_dir == (repo_root / "grammars" / "toy").resolve()
        assert paths.output_so == (repo_root / "build" / "toy" / "toy.so").resolve()

    def test_workflow_paths_rejects_noncanonical_output_so(self, tmp_path: Path) -> None:
        repo_root = _make_repo_layout(tmp_path)
        _make_grammar(repo_root, "toy")

        with pytest.raises(ValidationError):
            WorkflowPaths(
                repo_root=repo_root,
                grammar="toy",
                output_so=(repo_root / "build" / "toy.so").resolve(),
            )

    def test_build_request_requires_generated_parser(self, tmp_path: Path) -> None:
        repo_root = _make_repo_layout(tmp_path)
        _make_grammar(repo_root, "toy")

        with pytest.raises(ValidationError):
            BuildRequest(paths=WorkflowPaths(repo_root=repo_root, grammar="toy"))

    def test_generate_request_requires_existing_grammar(self, tmp_path: Path) -> None:
        repo_root = _make_repo_layout(tmp_path)
        _make_grammar(repo_root, "toy")

        request = GenerateRequest(paths=WorkflowPaths(repo_root=repo_root, grammar="toy"))
        assert request.paths.grammar == "toy"

    def test_generate_and_build_results_validate_artifacts(self, tmp_path: Path) -> None:
        repo_root = _make_repo_layout(tmp_path)
        grammar_dir = _make_grammar(repo_root, "toy")
        parser_c = grammar_dir / "src" / "parser.c"
        parser_c.write_text("/* parser */")

        paths = WorkflowPaths(repo_root=repo_root, grammar="toy")
        execution = CommandExecutionMetadata(duration_ms=10, command_line=["tree-sitter", "generate"])
        diagnostic = Diagnostic(message="ok", level="info")

        generate_result = GenerateResult(
            status="success",
            paths=paths,
            execution=execution,
            diagnostics=[diagnostic],
            generated_parser_c=parser_c.resolve(),
        )
        assert generate_result.generated_parser_c == paths.parser_c

        so_path = repo_root / "build" / "toy" / "toy.so"
        so_path.parent.mkdir(parents=True, exist_ok=True)
        so_path.write_text("binary")

        build_result = BuildResult(
            status="success",
            paths=paths,
            execution=CommandExecutionMetadata(
                duration_ms=25,
                command_line=["gcc", "-shared"],
                tool_versions={"gcc": "13.2.0", "tree-sitter": "0.25.2"},
            ),
            diagnostics=[],
            output_so=so_path.resolve(),
        )
        assert build_result.output_so == paths.output_so

    def test_parse_and_test_requests_require_expected_artifacts(self, tmp_path: Path) -> None:
        repo_root = _make_repo_layout(tmp_path)
        grammar_dir = _make_grammar(repo_root, "toy")
        parser_c = grammar_dir / "src" / "parser.c"
        parser_c.write_text("/* parser */")

        so_path = repo_root / "build" / "toy" / "toy.so"
        so_path.parent.mkdir(parents=True, exist_ok=True)
        so_path.write_text("binary")

        corpus_dir = grammar_dir / "test" / "corpus"
        corpus_dir.mkdir(parents=True, exist_ok=True)
        (corpus_dir / "basic.txt").write_text("====\ncontent\n")

        source_file = repo_root / "sample.txt"
        source_file.write_text("hello")

        paths = WorkflowPaths(repo_root=repo_root, grammar="toy")
        parse_request = ParseRequest(paths=paths, source_file=source_file)
        assert parse_request.source_file == source_file

        test_request = TestGrammarRequest(paths=paths)
        assert test_request.paths.corpus_dir == corpus_dir.resolve()

    def test_parse_result_and_doctor_contracts(self, tmp_path: Path) -> None:
        repo_root = _make_repo_layout(tmp_path)
        _make_grammar(repo_root, "toy")

        paths = WorkflowPaths(repo_root=repo_root, grammar="toy")
        execution = CommandExecutionMetadata(duration_ms=4, command_line=["tree-sitter", "parse"])

        parse_result = ParseResult(
            status="success",
            paths=paths,
            execution=execution,
            diagnostics=[Diagnostic(message="Recovered parse error", level="warning")],
            source_file=(repo_root / "sample.txt"),
            node_count=2,
            has_errors=True,
            root_node_type="source_file",
        )
        assert parse_result.has_errors is True

        doctor_request = DoctorRequest(paths=paths)
        assert doctor_request.paths.grammar == "toy"

        doctor_result = DoctorResult(
            status="failure",
            paths=paths,
            execution=CommandExecutionMetadata(duration_ms=7, command_line=["just", "doctor", "toy"]),
            diagnostics=[Diagnostic(message="Missing parser", level="error")],
            findings=["Parser not generated"],
        )
        assert doctor_result.findings == ["Parser not generated"]

    def test_test_grammar_result_counters_are_non_negative(self, tmp_path: Path) -> None:
        repo_root = _make_repo_layout(tmp_path)
        _make_grammar(repo_root, "toy")
        paths = WorkflowPaths(repo_root=repo_root, grammar="toy")

        with pytest.raises(ValidationError):
            TestGrammarResult(
                status="failure",
                paths=paths,
                execution=CommandExecutionMetadata(duration_ms=11, command_line=["tree-sitter", "test"]),
                diagnostics=[],
                passed=1,
                failed=-1,
            )
