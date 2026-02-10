"""Pydantic data models for Grammatic build and parse event logs.

These models define the structured, append-only JSONL schema used by the
Phase 1 logging pipeline.
"""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, Field


class GrammarMetadata(BaseModel):
    """Canonical metadata describing a tracked tree-sitter grammar source."""

    grammar_name: str = Field(description="Short local identifier for the grammar.")
    grammar_repo_url: str = Field(description="Remote git URL for the grammar repository.")
    grammar_commit: str = Field(description="Resolved git commit hash for the grammar build.")


class BuildLogEntry(BaseModel):
    """Single build event recorded when a grammar is compiled into a shared object."""

    event_type: Literal["build"] = "build"
    timestamp: datetime = Field(description="UTC timestamp when the build event was recorded.")
    grammar_name: str = Field(description="Grammar name being built.")
    grammar_commit: str = Field(description="Grammar commit hash used for this build.")
    grammar_repo_url: str = Field(description="Grammar git remote URL used for this build.")
    grammar_dir: Path = Field(description="Filesystem path to the grammar source directory.")
    output_path: Path = Field(description="Filesystem path to the compiled shared library output.")
    compiler: Literal["gcc", "g++"] = Field(
        description="Compiler selected for the build based on scanner source type."
    )
    build_time_ms: int = Field(ge=0, description="Build duration in milliseconds.")
    success: bool = Field(description="Whether the build command completed successfully.")


class ParseLogEntry(BaseModel):
    """Single parse event recorded when source input is parsed by a built grammar."""

    event_type: Literal["parse"] = "parse"
    timestamp: datetime = Field(description="UTC timestamp when the parse event was recorded.")
    grammar_name: str = Field(description="Grammar used to parse the input file.")
    grammar_version: str = Field(
        description="Grammar commit version associated with the parse, or 'unknown'."
    )
    source_file: Path = Field(description="Filesystem path to the parsed source file.")
    parse_time_ms: int = Field(ge=0, description="Parse duration in milliseconds.")
    node_count: int = Field(ge=0, description="Total number of nodes in the produced AST.")
    has_errors: bool = Field(description="Whether the parse output contains ERROR nodes.")
    success: bool = Field(description="Whether the parse command completed successfully.")
