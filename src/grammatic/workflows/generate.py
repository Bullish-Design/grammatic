from __future__ import annotations

from grammatic.contracts import Diagnostic, GenerateRequest, GenerateResult
from grammatic.workspace import WorkshopLayout

from .common import now_ms, run


def handle_generate(request: GenerateRequest) -> GenerateResult:
    started = now_ms()
    layout = WorkshopLayout(repo_root=request.repo_root)
    workspace = layout.for_grammar(request.grammar)

    result = run(["tree-sitter", "generate"], cwd=workspace.grammar_dir)
    duration = now_ms() - started
    diagnostics: list[Diagnostic] = []
    if result.stdout.strip():
        diagnostics.append(Diagnostic(level="info", message=result.stdout.strip()))
    if result.stderr.strip():
        diagnostics.append(Diagnostic(level="info" if result.returncode == 0 else "error", message=result.stderr.strip()))

    return GenerateResult(
        status="ok" if result.returncode == 0 else "error",
        grammar=request.grammar,
        grammar_dir=workspace.grammar_dir,
        duration_ms=duration,
        diagnostics=diagnostics,
    )
