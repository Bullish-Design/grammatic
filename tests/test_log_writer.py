from __future__ import annotations

import json
from pathlib import Path

import pytest

from grammatic.event_logs import build_event, parse_event
from grammatic.workflows.common import count_nodes, detect_compiler, has_errors

PROJECT_ROOT = Path(__file__).resolve().parents[1]


class TestBuildEventGeneration:
    """Test build event generation."""

    def test_build_log_structure(self, tmp_path: Path) -> None:
        """Build events have required fields."""
        grammar_dir = tmp_path / "grammars" / "test"
        (grammar_dir / "src").mkdir(parents=True)

        event = build_event(
            grammar="test",
            commit="abc123",
            repo_url="https://example.com/test",
            so_path=tmp_path / "build" / "test" / "test.so",
            compiler="gcc",
            tree_sitter_version="1.0.0",
            status="success",
            duration_ms=100,
        )

        assert event.event_type == "build"
        assert event.grammar == "test"
        assert event.status == "success"
        assert event.duration_ms == 100
        assert event.compiler == "gcc"

    def test_build_log_with_failure(self, tmp_path: Path) -> None:
        """Build events can record failures."""
        event = build_event(
            grammar="test",
            commit="abc123",
            repo_url="https://example.com/test",
            so_path=tmp_path / "build" / "test" / "test.so",
            compiler="gcc",
            tree_sitter_version="1.0.0",
            status="failure",
            duration_ms=50,
            error_code="COMPILATIONERROR",
            stderr_excerpt="compilation failed",
        )

        assert event.status == "failure"
        assert event.error_code == "COMPILATIONERROR"
        assert event.stderr_excerpt == "compilation failed"


class TestParseEventGeneration:
    """Test parse event generation."""

    def test_parse_log_structure(self, tmp_path: Path) -> None:
        """Parse events have required fields."""
        source_file = tmp_path / "test.txt"
        source_file.write_text("test content")

        event = parse_event(
            grammar="test",
            grammar_version="v1.0.0",
            source_file=source_file,
            node_count=10,
            has_errors=False,
            root_node_type="source_file",
            status="success",
            duration_ms=25,
        )

        assert event.event_type == "parse"
        assert event.grammar == "test"
        assert event.grammar_version == "v1.0.0"
        assert event.node_count == 10
        assert event.has_errors is False
        assert event.status == "success"

    def test_parse_with_errors(self, tmp_path: Path) -> None:
        """Parse events can indicate parsing errors."""
        source_file = tmp_path / "test.txt"
        source_file.write_text("test")

        event = parse_event(
            grammar="test",
            grammar_version="v1.0.0",
            source_file=source_file,
            node_count=5,
            has_errors=True,
            root_node_type="source_file",
            status="success",
            duration_ms=15,
        )

        assert event.has_errors is True


class TestErrorDetection:
    """Test parse tree error detection utilities."""

    def test_error_node_detection(self) -> None:
        """has_errors() detects ERROR nodes in parse tree."""
        tree_with_error = {
            "type": "source_file",
            "children": [{"type": "line", "children": []}, {"type": "ERROR", "children": []}],
        }

        assert has_errors(tree_with_error) is True

    def test_no_error_detection(self) -> None:
        """has_errors() returns False for valid parse tree."""
        tree_without_error = {
            "type": "source_file",
            "children": [{"type": "line", "children": []}, {"type": "line", "children": []}],
        }

        assert has_errors(tree_without_error) is False


class TestNodeCounting:
    """Test parse tree node counting utilities."""

    def test_node_counting(self) -> None:
        """count_nodes() recursively counts all nodes."""
        tree = {
            "type": "source_file",
            "children": [
                {"type": "line", "children": [{"type": "word", "children": []}]},
                {"type": "line", "children": []},
            ],
        }

        # Root + 2 lines + 1 word = 4 nodes
        assert count_nodes(tree) == 4

    def test_empty_tree_counting(self) -> None:
        """count_nodes() handles empty trees."""
        tree = {"type": "source_file", "children": []}

        assert count_nodes(tree) == 1


class TestCompilerDetection:
    """Test compiler detection utilities."""

    def test_detect_cpp_scanner(self, tmp_path: Path) -> None:
        """detect_compiler() identifies C++ scanner."""
        grammar_dir = tmp_path / "grammar"
        (grammar_dir / "src").mkdir(parents=True)
        (grammar_dir / "src" / "scanner.cc").touch()

        compiler = detect_compiler(grammar_dir)
        assert compiler == "g++"

    def test_detect_c_scanner(self, tmp_path: Path) -> None:
        """detect_compiler() identifies C scanner."""
        grammar_dir = tmp_path / "grammar"
        (grammar_dir / "src").mkdir(parents=True)
        (grammar_dir / "src" / "scanner.c").touch()

        compiler = detect_compiler(grammar_dir)
        assert compiler == "gcc"

    def test_detect_no_scanner(self, tmp_path: Path) -> None:
        """detect_compiler() defaults to gcc when no scanner."""
        grammar_dir = tmp_path / "grammar"
        (grammar_dir / "src").mkdir(parents=True)

        compiler = detect_compiler(grammar_dir)
        assert compiler == "gcc"
