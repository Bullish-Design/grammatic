"""Pydantic data models for Grammatic build and parse event logs."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, Field


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
    build_success: bool = Field(description="Whether the build command completed successfully.")
    build_time_ms: int = Field(ge=0, description="Build duration in milliseconds.")
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
    parse_time_ms: int = Field(ge=0, description="Parse duration in milliseconds.")
    root_node_type: str = Field(description="Type of the parse tree root node.")
