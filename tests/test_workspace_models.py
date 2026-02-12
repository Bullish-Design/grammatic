from __future__ import annotations

from pathlib import Path

import pytest
from pydantic import ValidationError

from grammatic.workspace import GrammarWorkspace, WorkshopLayout


def _make_repo_layout(tmp_path: Path) -> Path:
    (tmp_path / "grammars").mkdir(parents=True, exist_ok=True)
    (tmp_path / "scripts").mkdir(parents=True, exist_ok=True)
    (tmp_path / "logs").mkdir(parents=True, exist_ok=True)
    return tmp_path


def _make_grammar(tmp_path: Path, grammar: str) -> Path:
    grammar_dir = tmp_path / "grammars" / grammar
    (grammar_dir / "src").mkdir(parents=True, exist_ok=True)
    (grammar_dir / "grammar.js").write_text("module.exports = grammar({name: 'toy', rules: {}});")
    return grammar_dir


class TestWorkshopLayout:
    def test_repo_layout_validation_succeeds_for_real_repo(self) -> None:
        layout = WorkshopLayout(repo_root=Path.cwd())

        assert layout.logs_dir == (Path.cwd() / "logs").resolve()
        assert layout.builds_log == (Path.cwd() / "logs" / "builds.jsonl").resolve()

    def test_repo_layout_validation_fails_when_required_dirs_missing(self, tmp_path: Path) -> None:
        with pytest.raises(ValidationError):
            WorkshopLayout(repo_root=tmp_path)


class TestGrammarWorkspace:
    def test_grammar_workspace_validation_succeeds_for_toy_grammar(self, tmp_path: Path) -> None:
        repo_root = _make_repo_layout(tmp_path)
        _make_grammar(repo_root, "toy")

        workspace = GrammarWorkspace(repo_root=repo_root, grammar="toy")

        assert workspace.grammar_dir == (repo_root / "grammars" / "toy").resolve()
        assert workspace.grammar_js.is_file()

    def test_grammar_workspace_validation_fails_for_missing_grammar(self, tmp_path: Path) -> None:
        repo_root = _make_repo_layout(tmp_path)

        with pytest.raises(ValidationError):
            GrammarWorkspace(repo_root=repo_root, grammar="does-not-exist")

    def test_grammar_workspace_validation_fails_for_missing_grammar_js(self, tmp_path: Path) -> None:
        repo_root = _make_repo_layout(tmp_path)
        grammar_dir = repo_root / "grammars" / "toy"
        src_dir = grammar_dir / "src"
        src_dir.mkdir(parents=True)

        with pytest.raises(ValidationError):
            GrammarWorkspace(repo_root=repo_root, grammar="toy")

    def test_layout_can_construct_grammar_workspace(self, tmp_path: Path) -> None:
        repo_root = _make_repo_layout(tmp_path)
        _make_grammar(repo_root, "toy")
        layout = WorkshopLayout(repo_root=repo_root)

        workspace = layout.for_grammar("toy")

        assert workspace.grammar == "toy"
