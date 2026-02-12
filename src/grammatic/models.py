"""Pydantic data models for Grammatic workflows and event logs."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


class Diagnostic(BaseModel):
    """Normalized diagnostic emitted by any workflow command."""

    message: str = Field(min_length=1, description="Human-readable diagnostic message.")
    severity: Literal["error", "warning", "info"] = Field(
        description="Normalized severity level for diagnostic reporting."
    )
    code: str | None = Field(default=None, description="Optional stable machine-readable diagnostic code.")
    remediation: str | None = Field(
        default=None,
        description="Optional actionable guidance describing how to remediate the issue.",
    )


class CommandExecutionMetadata(BaseModel):
    """Execution metadata for a command run by a workflow."""

    duration_ms: int = Field(ge=0, description="Command runtime in milliseconds.")
    command_line: list[str] = Field(min_length=1, description="Executed command and arguments.")
    exit_code: int | None = Field(default=None, description="Process exit code when available.")
    tool_versions: dict[str, str] = Field(
        default_factory=dict,
        description="Tool version map (for example tree-sitter, gcc, g++), when relevant.",
    )


class WorkflowPaths(BaseModel):
    """Resolved canonical filesystem paths for a grammar workflow."""

    model_config = ConfigDict(frozen=True)

    repo_root: Path = Field(description="Repository root containing grammars/, build/, and logs/.")
    grammar: str = Field(min_length=1, description="Grammar identifier used in grammar-name-first UX.")
    grammar_dir: Path | None = Field(default=None, description="Resolved grammar directory path.")
    src_dir: Path | None = Field(default=None, description="Resolved grammar src directory path.")
    grammar_js: Path | None = Field(default=None, description="Resolved grammar.js source path.")
    parser_c: Path | None = Field(default=None, description="Resolved generated parser.c path.")
    build_dir: Path | None = Field(default=None, description="Resolved build output directory path.")
    output_so: Path | None = Field(default=None, description="Resolved canonical shared-library output path.")
    corpus_dir: Path | None = Field(default=None, description="Resolved corpus test directory path.")

    @model_validator(mode="before")
    @classmethod
    def populate_paths(cls, data: Any) -> Any:
        if not isinstance(data, dict):
            return data

        repo_root = Path(data["repo_root"]).resolve()
        grammar = data["grammar"]
        grammar_dir = (repo_root / "grammars" / grammar).resolve()

        data.setdefault("grammar_dir", grammar_dir)
        data.setdefault("src_dir", (grammar_dir / "src").resolve())
        data.setdefault("grammar_js", (grammar_dir / "grammar.js").resolve())
        data.setdefault("parser_c", (grammar_dir / "src" / "parser.c").resolve())
        data.setdefault("build_dir", (repo_root / "build" / grammar).resolve())
        data.setdefault("output_so", (repo_root / "build" / grammar / f"{grammar}.so").resolve())
        data.setdefault("corpus_dir", (grammar_dir / "test" / "corpus").resolve())
        return data

    @model_validator(mode="after")
    def validate_canonical(self) -> WorkflowPaths:
        expected_grammar_dir = (self.repo_root / 'grammars' / self.grammar).resolve()
        expected_src_dir = (expected_grammar_dir / 'src').resolve()
        expected_grammar_js = (expected_grammar_dir / 'grammar.js').resolve()
        expected_parser_c = (expected_src_dir / 'parser.c').resolve()
        expected_build_dir = (self.repo_root / 'build' / self.grammar).resolve()
        expected_output_so = (expected_build_dir / f'{self.grammar}.so').resolve()
        expected_corpus_dir = (expected_grammar_dir / 'test' / 'corpus').resolve()

        if self.grammar_dir != expected_grammar_dir:
            raise ValueError(f'grammar_dir must resolve to grammars/<grammar>: {expected_grammar_dir}')
        if self.src_dir != expected_src_dir:
            raise ValueError(f'src_dir must resolve to grammars/<grammar>/src: {expected_src_dir}')
        if self.grammar_js != expected_grammar_js:
            raise ValueError(f'grammar_js must resolve to grammars/<grammar>/grammar.js: {expected_grammar_js}')
        if self.parser_c != expected_parser_c:
            raise ValueError(f'parser_c must resolve to grammars/<grammar>/src/parser.c: {expected_parser_c}')
        if self.build_dir != expected_build_dir:
            raise ValueError(f'build_dir must resolve to build/<grammar>: {expected_build_dir}')
        if self.output_so != expected_output_so:
            raise ValueError(f'output_so must resolve to build/<grammar>/<grammar>.so: {expected_output_so}')
        if self.corpus_dir != expected_corpus_dir:
            raise ValueError(f'corpus_dir must resolve to grammars/<grammar>/test/corpus: {expected_corpus_dir}')
        return self

    def require_grammar_exists(self) -> None:
        if not self.grammar_dir or not self.grammar_dir.is_dir():
            raise ValueError(
                f"Grammar directory not found: {self.grammar_dir}. Expected grammars/<grammar> to exist."
            )
        if not self.src_dir or not self.src_dir.is_dir():
            raise ValueError(f"Grammar source directory not found: {self.src_dir}")
        if not self.grammar_js or not self.grammar_js.is_file():
            raise ValueError(f"Missing grammar.js: {self.grammar_js}")


class WorkflowRequest(BaseModel):
    """Base request contract for grammar-name-first workflow commands."""

    paths: WorkflowPaths


class WorkflowResult(BaseModel):
    """Base result contract for workflow command outcomes."""

    status: Literal["success", "failure"]
    paths: WorkflowPaths
    execution: CommandExecutionMetadata
    diagnostics: list[Diagnostic] = Field(default_factory=list)


class GenerateRequest(WorkflowRequest):
    @model_validator(mode="after")
    def validate_generate_request(self) -> GenerateRequest:
        self.paths.require_grammar_exists()
        return self


class GenerateResult(WorkflowResult):
    generated_parser_c: Path

    @model_validator(mode="after")
    def validate_generate_result(self) -> GenerateResult:
        if self.generated_parser_c != self.paths.parser_c:
            raise ValueError(f"generated_parser_c must be canonical parser path: {self.paths.parser_c}")
        if self.status == "success" and not self.generated_parser_c.is_file():
            raise ValueError(f"Generate succeeded but parser.c is missing: {self.generated_parser_c}")
        return self


class BuildRequest(WorkflowRequest):
    @model_validator(mode="after")
    def validate_build_request(self) -> BuildRequest:
        self.paths.require_grammar_exists()
        if not self.paths.parser_c or not self.paths.parser_c.is_file():
            raise ValueError(
                f"Missing generated parser.c: {self.paths.parser_c}. Run `just generate {self.paths.grammar}` first."
            )
        return self


class BuildResult(WorkflowResult):
    output_so: Path

    @model_validator(mode="after")
    def validate_build_result(self) -> BuildResult:
        if self.output_so != self.paths.output_so:
            raise ValueError(f"output_so must use canonical path: {self.paths.output_so}")
        if self.status == "success" and not self.output_so.is_file():
            raise ValueError(f"Build succeeded but shared library is missing: {self.output_so}")
        return self


class ParseRequest(WorkflowRequest):
    source_file: Path

    @model_validator(mode="after")
    def validate_parse_request(self) -> ParseRequest:
        self.paths.require_grammar_exists()
        if not self.paths.output_so or not self.paths.output_so.is_file():
            raise ValueError(
                f"Missing built shared object: {self.paths.output_so}. Run `just build {self.paths.grammar}` first."
            )
        if not self.source_file.is_file():
            raise ValueError(f"Source file not found for parse request: {self.source_file}")
        return self


class ParseResult(WorkflowResult):
    source_file: Path
    node_count: int = Field(ge=0)
    has_errors: bool
    root_node_type: str


class TestGrammarRequest(WorkflowRequest):
    __test__ = False

    @model_validator(mode="after")
    def validate_test_request(self) -> TestGrammarRequest:
        self.paths.require_grammar_exists()
        if not self.paths.parser_c or not self.paths.parser_c.is_file():
            raise ValueError(
                f"Missing generated parser.c: {self.paths.parser_c}. Run `just generate {self.paths.grammar}` first."
            )
        if not self.paths.output_so or not self.paths.output_so.is_file():
            raise ValueError(
                f"Missing built shared object: {self.paths.output_so}. Run `just build {self.paths.grammar}` first."
            )
        if not self.paths.corpus_dir or not self.paths.corpus_dir.is_dir():
            raise ValueError(f"Missing corpus directory: {self.paths.corpus_dir}")
        if not list(self.paths.corpus_dir.glob("*.txt")):
            raise ValueError(f"No corpus test files found in: {self.paths.corpus_dir}")
        return self


class TestGrammarResult(WorkflowResult):
    __test__ = False

    passed: int = Field(ge=0)
    failed: int = Field(ge=0)


class DoctorRequest(WorkflowRequest):
    @model_validator(mode="after")
    def validate_doctor_request(self) -> DoctorRequest:
        self.paths.require_grammar_exists()
        return self


class DoctorResult(WorkflowResult):
    findings: list[str] = Field(default_factory=list)


class GrammarMetadata(BaseModel):
    """Metadata describing a tracked tree-sitter grammar source."""

    name: str = Field(description="Short local identifier for the grammar.")
    submodule_path: Path = Field(description="Filesystem path to the grammar submodule.")
    current_commit: str = Field(description="Current git commit hash for the grammar source.")
    remote_url: str = Field(description="Remote git URL for the grammar repository.")
    last_build_timestamp: datetime | None = Field(
        default=None,
        description="Timestamp of the most recent successful build, if any.",
    )
    so_exists: bool = Field(description="Whether a compiled shared library currently exists.")


class BuildLogEntry(BaseModel):
    """Single build event recorded when a grammar is compiled into a shared object."""

    event_type: Literal["build"] = "build"
    timestamp: datetime = Field(description="Timestamp when the build event was recorded.")
    grammar: str = Field(description="Grammar name being built.")
    commit: str = Field(description="Grammar commit hash used for this build.")
    repo_url: str = Field(description="Grammar git remote URL used for this build.")
    so_path: Path = Field(description="Filesystem path to the compiled shared library output.")
    status: Literal["success", "failure"] = Field(
        description="Normalized workflow status for build events."
    )
    duration_ms: int = Field(ge=0, description="Build duration in milliseconds.")
    error_code: str | None = Field(default=None, description="Optional stable machine-readable error code.")
    stderr_excerpt: str | None = Field(default=None, description="Optional stderr excerpt for failed runs.")
    diagnostics: list[Diagnostic] = Field(default_factory=list)
    compiler: Literal["gcc", "g++"] = Field(
        description="Compiler selected for the build based on scanner source type."
    )
    tree_sitter_version: str = Field(description="Tree-sitter CLI version used for generation/build.")


class ParseLogEntry(BaseModel):
    """Single parse event recorded when source input is parsed by a built grammar."""

    event_type: Literal["parse"] = "parse"
    timestamp: datetime = Field(description="Timestamp when the parse event was recorded.")
    grammar: str = Field(description="Grammar used to parse the input file.")
    grammar_version: str = Field(
        description="Grammar commit version associated with the parse, or 'unknown'."
    )
    source_file: Path = Field(description="Filesystem path to the parsed source file.")
    node_count: int = Field(ge=0, description="Total number of nodes in the produced AST.")
    has_errors: bool = Field(description="Whether the parse output contains ERROR nodes.")
    status: Literal["success", "failure"] = Field(
        description="Normalized workflow status for parse events."
    )
    duration_ms: int = Field(ge=0, description="Parse duration in milliseconds.")
    error_code: str | None = Field(default=None, description="Optional stable machine-readable error code.")
    stderr_excerpt: str | None = Field(default=None, description="Optional stderr excerpt for failed runs.")
    diagnostics: list[Diagnostic] = Field(default_factory=list)
    root_node_type: str = Field(description="Type of the parse tree root node.")
