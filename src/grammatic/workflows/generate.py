from __future__ import annotations

from pydantic import ValidationError as PydanticValidationError

from grammatic.contracts import Diagnostic, GenerateRequest, GenerateResult
from grammatic.errors import ValidationError
from grammatic.workspace import WorkshopLayout

from .common import now_ms, run_checked


def handle_generate(request: GenerateRequest) -> GenerateResult:
    started = now_ms()
    try:
        layout = WorkshopLayout(repo_root=request.repo_root)
        workspace = layout.for_grammar(request.grammar)
    except (ValueError, PydanticValidationError) as exc:
        raise ValidationError(str(exc)) from exc

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
