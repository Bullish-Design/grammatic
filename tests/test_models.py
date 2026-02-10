from __future__ import annotations

from datetime import datetime
from pathlib import Path

import pytest
from pydantic import ValidationError

from grammatic.models import BuildLogEntry, GrammarMetadata, ParseLogEntry


class TestBuildLogEntry:
    def test_valid_construction(self) -> None:
        entry = BuildLogEntry(
            timestamp=datetime.now(),
            grammar="python",
            commit="abc123",
            repo_url="https://github.com/tree-sitter/tree-sitter-python",
            so_path=Path("build/python.so"),
            build_success=True,
            build_time_ms=1234,
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
                build_success=True,
                build_time_ms=1234,
                compiler="clang",
                tree_sitter_version="0.21.0",
            )

    def test_json_serialization_contains_expected_fields(self) -> None:
        entry = BuildLogEntry(
            timestamp=datetime(2026, 2, 10, 15, 30, 45),
            grammar="python",
            commit="abc123",
            repo_url="https://github.com/tree-sitter/tree-sitter-python",
            so_path=Path("build/python.so"),
            build_success=True,
            build_time_ms=1234,
            compiler="gcc",
            tree_sitter_version="0.21.0",
        )

        json_payload = entry.model_dump_json()

        assert '"event_type":"build"' in json_payload
        assert '"grammar":"python"' in json_payload
        assert '"commit":"abc123"' in json_payload


class TestParseLogEntry:
    def test_valid_construction(self) -> None:
        entry = ParseLogEntry(
            timestamp=datetime.now(),
            grammar="python",
            grammar_version="abc123",
            source_file=Path("tests/fixtures/sample.py"),
            node_count=42,
            has_errors=False,
            parse_time_ms=12,
            root_node_type="module",
        )

        assert entry.event_type == "parse"
        assert entry.has_errors is False

    def test_explicit_error_case(self) -> None:
        entry = ParseLogEntry(
            timestamp=datetime.now(),
            grammar="python",
            grammar_version="abc123",
            source_file=Path("tests/fixtures/invalid.py"),
            node_count=10,
            has_errors=True,
            parse_time_ms=7,
            root_node_type="ERROR",
        )

        assert entry.has_errors is True
        assert entry.root_node_type == "ERROR"

    def test_json_serialization_checks(self) -> None:
        entry = ParseLogEntry(
            timestamp=datetime(2026, 2, 10, 15, 31, 12),
            grammar="python",
            grammar_version="abc123",
            source_file=Path("tests/fixtures/sample.py"),
            node_count=42,
            has_errors=False,
            parse_time_ms=12,
            root_node_type="module",
        )

        json_payload = entry.model_dump_json()

        assert '"event_type":"parse"' in json_payload
        assert '"root_node_type":"module"' in json_payload
        assert '"has_errors":false' in json_payload


class TestGrammarMetadata:
    def test_valid_metadata_with_build_timestamp(self) -> None:
        metadata = GrammarMetadata(
            name="python",
            submodule_path=Path("grammars/python"),
            current_commit="abc123",
            remote_url="https://github.com/tree-sitter/tree-sitter-python",
            last_build_timestamp=datetime.now(),
            so_exists=True,
        )

        assert metadata.name == "python"
        assert metadata.so_exists is True

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
