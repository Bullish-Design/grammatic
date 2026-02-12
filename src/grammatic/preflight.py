from __future__ import annotations

from pathlib import Path

from pydantic import ValidationError as PydanticValidationError

from grammatic.errors import ArtifactMissingError, ToolMissingError, ValidationError
from grammatic.workspace import GrammarWorkspace, WorkshopLayout
from grammatic.workflows.common import ensure_tool, run


def resolve_workshop_layout(repo_root: Path) -> WorkshopLayout:
    """Resolve and validate repository-level paths from repo root."""

    try:
        return WorkshopLayout(repo_root=repo_root)
    except (ValueError, PydanticValidationError) as exc:
        raise ValidationError(str(exc)) from exc


def resolve_grammar_workspace(repo_root: Path, grammar: str) -> tuple[WorkshopLayout, GrammarWorkspace]:
    """Resolve grammar-name-first workspace paths from repo root."""

    layout = resolve_workshop_layout(repo_root)
    try:
        workspace = layout.for_grammar(grammar)
    except (ValueError, PydanticValidationError) as exc:
        raise ValidationError(str(exc)) from exc
    return layout, workspace


def ensure_required_paths_for_generate(workspace: GrammarWorkspace) -> None:
    if not workspace.grammar_js.is_file():
        raise ValidationError(
            f"Missing grammar.js: {workspace.grammar_js}. "
            f"Run `just add-grammar {workspace.grammar}` or check the grammar source."
        )


def ensure_required_paths_for_build(workspace: GrammarWorkspace) -> None:
    parser_c = workspace.src_dir / "parser.c"
    if not parser_c.is_file():
        raise ArtifactMissingError(
            f"Generated parser not found: {parser_c}. Run 'just generate {workspace.grammar}' first"
        )


def ensure_required_paths_for_parse(workspace: GrammarWorkspace, source: Path) -> Path:
    resolved = source.resolve()
    if not workspace.so_path.is_file():
        raise ArtifactMissingError(
            f"Built grammar not found: {workspace.so_path}. Run 'just build {workspace.grammar}' first"
        )
    if not resolved.is_file():
        raise ValidationError(f"Source file not found: {resolved}")
    return resolved


def ensure_required_paths_for_test(workspace: GrammarWorkspace) -> None:
    corpus_dir = workspace.grammar_dir / "test" / "corpus"
    if not corpus_dir.is_dir():
        raise ValidationError(f"No corpus tests found for {workspace.grammar}")
    if not workspace.so_path.is_file():
        raise ArtifactMissingError(
            f"Built grammar not found: {workspace.so_path}. Run 'just build {workspace.grammar}' first"
        )


def ensure_tools_for_generate() -> None:
    ensure_tool("tree-sitter")


def ensure_tools_for_build(workspace: GrammarWorkspace) -> None:
    ensure_tool("g++" if (workspace.src_dir / "scanner.cc").is_file() else "gcc")


def ensure_tools_for_parse() -> None:
    ensure_tool("tree-sitter")


def ensure_tools_for_test() -> None:
    ensure_tool("tree-sitter")


def ensure_tree_sitter_test_language_support() -> None:
    help_result = run(["tree-sitter", "test", "--help"])
    if help_result.returncode != 0:
        raise ToolMissingError("Failed to inspect tree-sitter test support via 'tree-sitter test --help'")
    if "--language" not in help_result.stdout:
        raise ValidationError(
            "Current tree-sitter CLI does not support 'tree-sitter test --language'. "
            "Upgrade tree-sitter to run corpus tests with a built grammar artifact"
        )
