"""Workspace validation models for grammar-name-first workflows."""

from __future__ import annotations

from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field, model_validator


class GrammarWorkspace(BaseModel):
    """Validated paths for a single grammar workspace in this repository."""

    model_config = ConfigDict(frozen=True)

    repo_root: Path = Field(description="Repository root containing grammars/, build/, and logs/.")
    grammar: str = Field(min_length=1, description="Grammar name used across commands and paths.")

    @model_validator(mode="after")
    def validate_workspace(self) -> GrammarWorkspace:
        grammar_dir = self.grammar_dir
        if not grammar_dir.is_dir():
            raise ValueError(
                f"Grammar directory not found: {grammar_dir}. Expected grammars/<grammar> to exist."
            )

        src_dir = self.src_dir
        if not src_dir.is_dir():
            raise ValueError(
                f"Grammar source directory not found: {src_dir}. Expected grammars/<grammar>/src."
            )

        grammar_js = self.grammar_js
        if not grammar_js.is_file():
            raise ValueError(
                f"Missing grammar.js: {grammar_js}. Run `just add-grammar {self.grammar}` or check the grammar source."
            )

        return self

    @property
    def grammar_dir(self) -> Path:
        return (self.repo_root / "grammars" / self.grammar).resolve()

    @property
    def src_dir(self) -> Path:
        return (self.grammar_dir / "src").resolve()

    @property
    def grammar_js(self) -> Path:
        return (self.grammar_dir / "grammar.js").resolve()

    @property
    def build_dir(self) -> Path:
        return (self.repo_root / "build" / self.grammar).resolve()

    @property
    def so_path(self) -> Path:
        return (self.build_dir / f"{self.grammar}.so").resolve()


class WorkshopLayout(BaseModel):
    """Validated repository-level layout for workshop orchestration."""

    model_config = ConfigDict(frozen=True)

    repo_root: Path = Field(description="Repository root.")

    @model_validator(mode="after")
    def validate_layout(self) -> WorkshopLayout:
        required_dirs = ["grammars", "scripts"]
        missing = [name for name in required_dirs if not (self.repo_root / name).is_dir()]
        if missing:
            joined = ", ".join(missing)
            raise ValueError(f"Repository layout is missing required directories: {joined}")
        return self

    @property
    def logs_dir(self) -> Path:
        return (self.repo_root / "logs").resolve()

    @property
    def builds_log(self) -> Path:
        return (self.logs_dir / "builds.jsonl").resolve()

    @property
    def parses_log(self) -> Path:
        return (self.logs_dir / "parses.jsonl").resolve()

    def for_grammar(self, grammar: str) -> GrammarWorkspace:
        return GrammarWorkspace(repo_root=self.repo_root, grammar=grammar)
