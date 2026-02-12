from __future__ import annotations

from pydantic import ValidationError as PydanticValidationError

from grammatic.contracts import Diagnostic, TestGrammarRequest, TestGrammarResult
from grammatic.errors import ArtifactMissingError, ValidationError
from grammatic.workspace import WorkshopLayout

from .common import now_ms, run_checked


def handle_test_grammar(request: TestGrammarRequest) -> TestGrammarResult:
    started = now_ms()
    try:
        layout = WorkshopLayout(repo_root=request.repo_root)
        workspace = layout.for_grammar(request.grammar)
    except (ValueError, PydanticValidationError) as exc:
        raise ValidationError(str(exc)) from exc

    corpus_dir = workspace.grammar_dir / "test" / "corpus"
    if not corpus_dir.is_dir():
        raise ValidationError(f"No corpus tests found for {request.grammar}")

    if not workspace.so_path.is_file():
        raise ArtifactMissingError(
            f"Built grammar not found: {workspace.so_path}. Run 'just build {request.grammar}' first"
        )

    help_result = run_checked(["tree-sitter", "test", "--help"], message="Failed to inspect tree-sitter test support")
    if "--language" not in help_result.stdout:
        raise ValidationError(
            "Current tree-sitter CLI does not support 'tree-sitter test --language'. "
            f"Upgrade tree-sitter to run corpus tests against {workspace.so_path}"
        )

    test_result = run_checked(
        ["tree-sitter", "test", "--language", str(workspace.so_path)],
        cwd=workspace.grammar_dir,
        message=f"tree-sitter test failed for grammar '{request.grammar}'",
    )
    duration = now_ms() - started
    diagnostics: list[Diagnostic] = []
    if test_result.stdout.strip():
        diagnostics.append(Diagnostic(level="info", message=test_result.stdout.strip()))
    if test_result.stderr.strip():
        diagnostics.append(Diagnostic(level="info", message=test_result.stderr.strip()))

    return TestGrammarResult(
        status="ok",
        grammar=request.grammar,
        duration_ms=duration,
        diagnostics=diagnostics,
    )
