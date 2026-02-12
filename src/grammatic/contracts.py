from __future__ import annotations

from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class Diagnostic(BaseModel):
    model_config = ConfigDict(frozen=True)

    level: Literal["info", "warning", "error"]
    message: str


class GenerateRequest(BaseModel):
    grammar: str = Field(min_length=1)
    repo_root: Path


class GenerateResult(BaseModel):
    status: Literal["ok", "error"]
    grammar: str
    grammar_dir: Path
    duration_ms: int = Field(ge=0)
    diagnostics: list[Diagnostic] = Field(default_factory=list)


class BuildRequest(BaseModel):
    grammar: str = Field(min_length=1)
    repo_root: Path


class BuildResult(BaseModel):
    status: Literal["ok", "error"]
    grammar: str
    artifact_path: Path
    compiler: Literal["gcc", "g++"]
    duration_ms: int = Field(ge=0)
    diagnostics: list[Diagnostic] = Field(default_factory=list)


class ParseRequest(BaseModel):
    grammar: str = Field(min_length=1)
    repo_root: Path
    source: Path


class ParseResult(BaseModel):
    status: Literal["ok", "error"]
    grammar: str
    source: Path
    parse_output: dict
    has_errors: bool
    node_count: int = Field(ge=0)
    duration_ms: int = Field(ge=0)
    diagnostics: list[Diagnostic] = Field(default_factory=list)


class TestGrammarRequest(BaseModel):
    grammar: str = Field(min_length=1)
    repo_root: Path


class TestGrammarResult(BaseModel):
    status: Literal["ok", "error"]
    grammar: str
    duration_ms: int = Field(ge=0)
    diagnostics: list[Diagnostic] = Field(default_factory=list)


class DoctorRequest(BaseModel):
    grammar: str = Field(min_length=1)
    repo_root: Path


class DoctorResult(BaseModel):
    status: Literal["ok", "error"]
    grammar: str
    findings: list[str] = Field(default_factory=list)
    duration_ms: int = Field(ge=0)
    diagnostics: list[Diagnostic] = Field(default_factory=list)
