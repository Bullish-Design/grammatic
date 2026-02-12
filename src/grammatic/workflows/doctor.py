from __future__ import annotations

from pydantic import ValidationError as PydanticValidationError

from grammatic.contracts import Diagnostic, DoctorRequest, DoctorResult
from grammatic.errors import ValidationError
from grammatic.workspace import WorkshopLayout

from .common import now_ms


def handle_doctor(request: DoctorRequest) -> DoctorResult:
    started = now_ms()
    try:
        layout = WorkshopLayout(repo_root=request.repo_root)
        workspace = layout.for_grammar(request.grammar)
    except (ValueError, PydanticValidationError) as exc:
        raise ValidationError(str(exc)) from exc

    issues: list[str] = []
    if not (workspace.src_dir / "parser.c").is_file():
        issues.append(f"Parser not generated. Run: just generate {request.grammar}")
    if not workspace.so_path.is_file():
        issues.append(f"Grammar not built. Run: just build {request.grammar}")

    corpus_dir = workspace.grammar_dir / "test" / "corpus"
    if not corpus_dir.is_dir():
        issues.append("No corpus tests directory")
    elif not list(corpus_dir.glob("*.txt")):
        issues.append("No corpus test files")

    has_scanner = (workspace.src_dir / "scanner.c").is_file() or (workspace.src_dir / "scanner.cc").is_file()
    grammar_js_text = workspace.grammar_js.read_text(encoding="utf-8")
    if not has_scanner and "externals:" in grammar_js_text:
        issues.append("Grammar uses externals but no scanner.c/scanner.cc found")

    duration = now_ms() - started
    diagnostics = [Diagnostic(level="error", message=issue) for issue in issues]
    if not diagnostics:
        diagnostics = [Diagnostic(level="info", message=f"✓ Grammar '{request.grammar}' looks good!")]

    return DoctorResult(
        status="ok" if not issues else "error",
        grammar=request.grammar,
        findings=issues,
        duration_ms=duration,
        diagnostics=diagnostics,
    )
