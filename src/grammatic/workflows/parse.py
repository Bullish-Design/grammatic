from __future__ import annotations

import json

from pydantic import ValidationError as PydanticValidationError

from grammatic.contracts import Diagnostic, ParseRequest, ParseResult
from grammatic.errors import ArtifactMissingError, ValidationError
from grammatic.workspace import WorkshopLayout

from .common import append_parse_log, count_nodes, has_errors, now_ms, run_checked


def handle_parse(request: ParseRequest) -> ParseResult:
    started = now_ms()
    try:
        layout = WorkshopLayout(repo_root=request.repo_root)
        workspace = layout.for_grammar(request.grammar)
    except (ValueError, PydanticValidationError) as exc:
        raise ValidationError(str(exc)) from exc

    if not workspace.so_path.is_file():
        raise ArtifactMissingError(
            f"Built grammar not found: {workspace.so_path}. Run 'just build {request.grammar}' first"
        )

    source = request.source.resolve()
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

    append_parse_log(layout, request.grammar, source, output, duration)
    root = output["root_node"]
    return ParseResult(
        status="ok",
        grammar=request.grammar,
        source=source,
        parse_output=output,
        has_errors=has_errors(root),
        node_count=count_nodes(root),
        duration_ms=duration,
        diagnostics=[Diagnostic(level="info", message="Parse logged to parses.jsonl")],
    )
