from __future__ import annotations

from grammatic.contracts import Diagnostic, TestGrammarRequest, TestGrammarResult
from grammatic.workspace import WorkshopLayout

from .common import now_ms, run


def handle_test_grammar(request: TestGrammarRequest) -> TestGrammarResult:
    started = now_ms()
    layout = WorkshopLayout(repo_root=request.repo_root)
    workspace = layout.for_grammar(request.grammar)
    corpus_dir = workspace.grammar_dir / "test" / "corpus"

    if not corpus_dir.is_dir():
        return TestGrammarResult(
            status="error",
            grammar=request.grammar,
            duration_ms=now_ms() - started,
            diagnostics=[Diagnostic(level="error", message=f"Error: No corpus tests found for {request.grammar}")],
        )

    if not workspace.so_path.is_file():
        return TestGrammarResult(
            status="error",
            grammar=request.grammar,
            duration_ms=now_ms() - started,
            diagnostics=[
                Diagnostic(
                    level="error",
                    message=f"Error: built grammar not found: {workspace.so_path}. Run 'just build {request.grammar}' first",
                )
            ],
        )

    help_result = run(["tree-sitter", "test", "--help"])
    if "--language" not in help_result.stdout:
        return TestGrammarResult(
            status="error",
            grammar=request.grammar,
            duration_ms=now_ms() - started,
            diagnostics=[
                Diagnostic(
                    level="error",
                    message=(
                        "Error: current tree-sitter CLI does not support 'tree-sitter test --language'. "
                        f"Upgrade tree-sitter to run corpus tests against {workspace.so_path}"
                    ),
                )
            ],
        )

    test_result = run(["tree-sitter", "test", "--language", str(workspace.so_path)], cwd=workspace.grammar_dir)
    duration = now_ms() - started
    diagnostics: list[Diagnostic] = []
    if test_result.stdout.strip():
        diagnostics.append(Diagnostic(level="info", message=test_result.stdout.strip()))
    if test_result.stderr.strip():
        diagnostics.append(Diagnostic(level="info" if test_result.returncode == 0 else "error", message=test_result.stderr.strip()))

    return TestGrammarResult(
        status="ok" if test_result.returncode == 0 else "error",
        grammar=request.grammar,
        duration_ms=duration,
        diagnostics=diagnostics,
    )
