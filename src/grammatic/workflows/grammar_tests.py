from __future__ import annotations

from grammatic.contracts import Diagnostic, TestGrammarRequest, TestGrammarResult
from grammatic.preflight import (
    ensure_required_paths_for_test,
    ensure_tools_for_test,
    resolve_grammar_workspace,
)

from .common import now_ms, run_checked


def handle_test_grammar(request: TestGrammarRequest) -> TestGrammarResult:
    started = now_ms()
    _, workspace = resolve_grammar_workspace(request.repo_root, request.grammar)

    ensure_required_paths_for_test(workspace)
    ensure_tools_for_test()

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
