from __future__ import annotations

import json
import os
from datetime import datetime
from pathlib import Path
from typing import Any

from grammatic.contracts import Diagnostic
from grammatic.errors import LogWriteError
from grammatic.models import BuildLogEntry, ParseLogEntry
from grammatic.workspace import WorkshopLayout


def append_jsonl_atomic(path: Path, payload: dict[str, Any]) -> None:
    """Append one JSON record to a JSONL file using atomic append semantics."""

    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        line = json.dumps(payload, separators=(",", ":"), default=str) + "\n"
        fd = os.open(path, os.O_APPEND | os.O_CREAT | os.O_WRONLY, 0o644)
        try:
            os.write(fd, line.encode("utf-8"))
        finally:
            os.close(fd)
    except OSError as exc:
        raise LogWriteError(f"Failed to write log entry: {exc}", path=path) from exc


def build_event(
    *,
    grammar: str,
    commit: str,
    repo_url: str,
    so_path: Path,
    compiler: str,
    tree_sitter_version: str,
    status: str,
    duration_ms: int,
    diagnostics: list[Diagnostic] | None = None,
    error_code: str | None = None,
    stderr_excerpt: str | None = None,
) -> BuildLogEntry:
    return BuildLogEntry(
        timestamp=datetime.now(),
        grammar=grammar,
        commit=commit,
        repo_url=repo_url,
        so_path=so_path,
        compiler=compiler,
        tree_sitter_version=tree_sitter_version,
        status=status,
        duration_ms=duration_ms,
        diagnostics=diagnostics or [],
        error_code=error_code,
        stderr_excerpt=stderr_excerpt,
    )


def parse_event(
    *,
    grammar: str,
    grammar_version: str,
    source_file: Path,
    node_count: int,
    has_errors: bool,
    root_node_type: str,
    status: str,
    duration_ms: int,
    diagnostics: list[Diagnostic] | None = None,
    error_code: str | None = None,
    stderr_excerpt: str | None = None,
) -> ParseLogEntry:
    return ParseLogEntry(
        timestamp=datetime.now(),
        grammar=grammar,
        grammar_version=grammar_version,
        source_file=source_file,
        node_count=node_count,
        has_errors=has_errors,
        root_node_type=root_node_type,
        status=status,
        duration_ms=duration_ms,
        diagnostics=diagnostics or [],
        error_code=error_code,
        stderr_excerpt=stderr_excerpt,
    )


def append_build_event(layout: WorkshopLayout, entry: BuildLogEntry) -> None:
    append_jsonl_atomic(layout.builds_log, entry.model_dump(mode="json"))


def append_parse_event(layout: WorkshopLayout, entry: ParseLogEntry) -> None:
    append_jsonl_atomic(layout.parses_log, entry.model_dump(mode="json"))
