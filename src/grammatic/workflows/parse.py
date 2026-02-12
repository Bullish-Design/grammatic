from __future__ import annotations

import json

from pydantic import ValidationError as PydanticValidationError

from grammatic.contracts import Diagnostic, ParseRequest, ParseResult
from grammatic.errors import ArtifactMissingError, GrammaticError, SubprocessExecutionError, ValidationError
from grammatic.event_logs import append_parse_event, parse_event
from grammatic.workspace import WorkshopLayout

from .common import count_nodes, has_errors, lookup_grammar_version, now_ms, run_checked


def _failure_details(exc: Exception) -> tuple[str, list[Diagnostic], str | None]:
    error_code = type(exc).__name__.upper()
    if isinstance(exc, SubprocessExecutionError):
        excerpt = exc.stderr or exc.stdout or str(exc)
    else:
        excerpt = str(exc)
    return error_code, [Diagnostic(level="error", message=str(exc))], excerpt[:400]


def handle_parse(request: ParseRequest) -> ParseResult:
    started = now_ms()
    try:
        layout = WorkshopLayout(repo_root=request.repo_root)
        workspace = layout.for_grammar(request.grammar)
    except (ValueError, PydanticValidationError) as exc:
        raise ValidationError(str(exc)) from exc

    source = request.source.resolve()
    grammar_version = lookup_grammar_version(request.grammar, layout.builds_log)

    try:
        if not workspace.so_path.is_file():
            raise ArtifactMissingError(
                f"Built grammar not found: {workspace.so_path}. Run 'just build {request.grammar}' first"
            )

        if not source.is_file():
            raise ValidationError(f"Source file not found: {source}")

        run_result = run_checked(
            ["tree-sitter", "parse", str(source), "--language", str(workspace.so_path), "--json"],
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
