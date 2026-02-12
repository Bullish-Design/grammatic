from __future__ import annotations

import json

from grammatic.contracts import Diagnostic, ParseRequest, ParseResult
from grammatic.workspace import WorkshopLayout

from .common import append_parse_log, count_nodes, has_errors, now_ms, run


def handle_parse(request: ParseRequest) -> ParseResult:
    started = now_ms()
    layout = WorkshopLayout(repo_root=request.repo_root)
    workspace = layout.for_grammar(request.grammar)

    if not workspace.so_path.is_file():
        return ParseResult(
            status="error",
            grammar=request.grammar,
            source=request.source,
            parse_output={},
            has_errors=True,
            node_count=0,
            duration_ms=now_ms() - started,
            diagnostics=[
                Diagnostic(
                    level="error",
                    message=f"Error: built grammar not found: {workspace.so_path}. Run 'just build {request.grammar}' first",
                )
            ],
        )

    source = request.source.resolve()
    if not source.is_file():
        return ParseResult(
            status="error",
            grammar=request.grammar,
            source=source,
            parse_output={},
            has_errors=True,
            node_count=0,
            duration_ms=now_ms() - started,
            diagnostics=[Diagnostic(level="error", message=f"Error: source file not found: {source}")],
        )

    run_result = run(["tree-sitter", "parse", str(source), "--language", str(workspace.so_path), "--json"])
    duration = now_ms() - started
    if run_result.returncode != 0:
        return ParseResult(
            status="error",
            grammar=request.grammar,
            source=source,
            parse_output={},
            has_errors=True,
            node_count=0,
            duration_ms=duration,
            diagnostics=[Diagnostic(level="error", message=run_result.stderr.strip() or "tree-sitter parse failed")],
        )

    try:
        output = json.loads(run_result.stdout)
    except json.JSONDecodeError:
        return ParseResult(
            status="error",
            grammar=request.grammar,
            source=source,
            parse_output={},
            has_errors=True,
            node_count=0,
            duration_ms=duration,
            diagnostics=[Diagnostic(level="error", message="Error: parse output is not valid JSON")],
        )

    if not isinstance(output, dict) or not isinstance(output.get("root_node"), dict):
        return ParseResult(
            status="error",
            grammar=request.grammar,
            source=source,
            parse_output={},
            has_errors=True,
            node_count=0,
            duration_ms=duration,
            diagnostics=[Diagnostic(level="error", message="Error: parse output is missing root_node")],
        )

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
