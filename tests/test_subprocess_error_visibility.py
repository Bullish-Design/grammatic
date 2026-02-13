from __future__ import annotations

from grammatic.errors import SubprocessExecutionError, bounded_output_excerpt
from grammatic.workflows.build import _failure_diagnostic
from grammatic.workflows.parse import _failure_details


def test_subprocess_error_str_includes_command_return_code_and_stderr_excerpt() -> None:
    exc = SubprocessExecutionError(
        command=["gcc", "parser.c"],
        returncode=1,
        stderr="fatal error: parser.c: No such file or directory",
        message="Failed to build grammar 'demo'",
    )

    message = str(exc)
    assert "Failed to build grammar 'demo'" in message
    assert "command=gcc parser.c" in message
    assert "return_code=1" in message
    assert "fatal error" in message


def test_subprocess_error_str_falls_back_to_stdout_excerpt() -> None:
    exc = SubprocessExecutionError(
        command=["tree-sitter", "parse", "missing.txt"],
        returncode=2,
        stderr="",
        stdout="parse failed: cannot read source",
        message="tree-sitter parse failed",
    )

    message = str(exc)
    assert "output=parse failed: cannot read source" in message


def test_bounded_output_excerpt_caps_length() -> None:
    text = "x" * 1200
    excerpt = bounded_output_excerpt(text, "", limit=500)
    assert len(excerpt) <= 501
    assert excerpt.endswith("…")


def test_build_failure_diagnostic_includes_command_and_output_excerpt() -> None:
    exc = SubprocessExecutionError(
        command=["gcc", "bad.c"],
        returncode=1,
        stderr="compiler exploded",
        message="Failed to build grammar 'demo'",
    )

    _, diagnostics, stderr_excerpt = _failure_diagnostic(exc)

    messages = [d.message for d in diagnostics]
    assert any(msg.startswith("command: gcc bad.c") for msg in messages)
    assert any(msg.startswith("output excerpt: compiler exploded") for msg in messages)
    assert stderr_excerpt == "compiler exploded"


def test_parse_failure_diagnostic_includes_command_and_output_excerpt() -> None:
    exc = SubprocessExecutionError(
        command=["tree-sitter", "parse", "demo.txt"],
        returncode=1,
        stderr="parse command failed",
        message="tree-sitter parse failed",
    )

    _, diagnostics, stderr_excerpt = _failure_details(exc)

    messages = [d.message for d in diagnostics]
    assert any(msg.startswith("command: tree-sitter parse demo.txt") for msg in messages)
    assert any(msg.startswith("output excerpt: parse command failed") for msg in messages)
    assert stderr_excerpt == "parse command failed"
