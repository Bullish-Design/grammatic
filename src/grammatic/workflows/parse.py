from __future__ import annotations

import json

from grammatic.contracts import Diagnostic, ParseRequest, ParseResult
from grammatic.errors import GrammaticError, SubprocessExecutionError, ValidationError, bounded_output_excerpt
from grammatic.event_logs import append_parse_event, parse_event
from grammatic.preflight import (
    ensure_required_paths_for_parse,
    ensure_tools_for_parse,
    ensure_tree_sitter_parse_support,
    resolve_grammar_workspace,
)

from .common import count_nodes, has_errors, lookup_grammar_version, now_ms, run_checked


def _failure_details(exc: Exception) -> tuple[str, list[Diagnostic], str | None]:
    error_code = type(exc).__name__.upper()
    if isinstance(exc, SubprocessExecutionError):
        excerpt = exc.excerpt()
        command = " ".join(exc.command)
        diagnostics = [
            Diagnostic(level="error", message=str(exc)),
            Diagnostic(level="error", message=f"command: {command}"),
        ]
        if excerpt:
            diagnostics.append(Diagnostic(level="error", message=f"output excerpt: {excerpt}"))
        return error_code, diagnostics, excerpt

    excerpt = bounded_output_excerpt(str(exc), "")
    return error_code, [Diagnostic(level="error", message=str(exc))], excerpt


def handle_parse(request: ParseRequest) -> ParseResult:
    started = now_ms()

    try:
        layout, workspace = resolve_grammar_workspace(request.repo_root, request.grammar)
        source = ensure_required_paths_for_parse(workspace, request.source)
        ensure_tools_for_parse()
        grammar_version = lookup_grammar_version(request.grammar, layout.builds_log)
        json_flag = ensure_tree_sitter_parse_support()

        run_result = run_checked(
            [
                "tree-sitter",
                "parse",
                str(source),
                "--lib-path",
                str(workspace.so_path),
                "--lang-name",
                request.grammar,
                json_flag,
            ],
            message="tree-sitter parse failed",
        )
        duration = now_ms() - started

        try:
            output = json.loads(run_result.stdout)
        except json.JSONDecodeError as exc:
            raise ValidationError("Parse output is not valid JSON") from exc

        if not isinstance(output, dict) or not isinstance(output.get("root_node"), dict):
            raise ValidationError("Parse output is missing root_node")

        root = output["root_node"]
        diagnostics = [Diagnostic(level="info", message="Parse logged to parses.jsonl")]

        append_parse_event(
            layout,
            parse_event(
                grammar=request.grammar,
                grammar_version=grammar_version,
                source_file=source,
                node_count=count_nodes(root),
                has_errors=has_errors(root),
                root_node_type=str(root.get("type", "unknown")),
                status="success",
                duration_ms=duration,
                diagnostics=diagnostics,
            ),
        )

        return ParseResult(
            status="ok",
            grammar=request.grammar,
            source=source,
            parse_output=output,
            has_errors=has_errors(root),
            node_count=count_nodes(root),
            duration_ms=duration,
            diagnostics=diagnostics,
        )
    except GrammaticError as exc:
        duration = now_ms() - started
        error_code, diagnostics, stderr_excerpt = _failure_details(exc)

        # Ensure we have layout and workspace for logging, use defaults if early failure
        try:
            layout, workspace = resolve_grammar_workspace(request.repo_root, request.grammar)
            grammar_version = lookup_grammar_version(request.grammar, layout.builds_log)
            # Handle source file that doesn't exist
            try:
                source = request.source.resolve()
            except Exception:
                source = request.source  # Use unresolved path if resolve fails
        except Exception:
            # If we can't resolve workspace, we can't log - just re-raise original error
            raise exc

        append_parse_event(
            layout,
            parse_event(
                grammar=request.grammar,
                grammar_version=grammar_version,
                source_file=source,
                node_count=0,
                has_errors=False,
                root_node_type="unknown",
                status="failure",
                duration_ms=duration,
                diagnostics=diagnostics,
                error_code=error_code,
                stderr_excerpt=stderr_excerpt,
            ),
        )
        raise
