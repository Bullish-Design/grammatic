from __future__ import annotations

from grammatic.contracts import Diagnostic, GenerateRequest, GenerateResult
from grammatic.preflight import (
    ensure_required_paths_for_generate,
    ensure_tools_for_generate,
    resolve_grammar_workspace,
)

from .common import now_ms, run_checked


def handle_generate(request: GenerateRequest) -> GenerateResult:
    started = now_ms()
    _, workspace = resolve_grammar_workspace(request.repo_root, request.grammar)
    ensure_required_paths_for_generate(workspace)
    ensure_tools_for_generate()

    result = run_checked(
        ["tree-sitter", "generate"],
        cwd=workspace.grammar_dir,
        message=f"tree-sitter generate failed for grammar '{request.grammar}'",
    )
    duration = now_ms() - started
    diagnostics: list[Diagnostic] = []
    if result.stdout.strip():
        diagnostics.append(Diagnostic(level="info", message=result.stdout.strip()))
    if result.stderr.strip():
        diagnostics.append(Diagnostic(level="info", message=result.stderr.strip()))

    return GenerateResult(
        status="ok",
        grammar=request.grammar,
        grammar_dir=workspace.grammar_dir,
        duration_ms=duration,
        diagnostics=diagnostics,
    )
