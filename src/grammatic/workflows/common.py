from __future__ import annotations

import json
import shutil
import subprocess
import time
from datetime import datetime
from pathlib import Path
from typing import Any

from grammatic.errors import LogWriteError, SubprocessExecutionError, ToolMissingError
from grammatic.models import BuildLogEntry, ParseLogEntry
from grammatic.workspace import WorkshopLayout


def now_ms() -> int:
    return int(time.time() * 1000)


def run(cmd: list[str], cwd: Path | None = None) -> subprocess.CompletedProcess[str]:
    return subprocess.run(cmd, cwd=cwd, check=False, capture_output=True, text=True)


def ensure_tool(tool: str) -> None:
    if shutil.which(tool) is None:
        raise ToolMissingError(f"Required tool not found in PATH: {tool}")


def run_checked(cmd: list[str], cwd: Path | None = None, *, message: str | None = None) -> subprocess.CompletedProcess[str]:
    ensure_tool(cmd[0])
    result = run(cmd, cwd=cwd)
    if result.returncode != 0:
        raise SubprocessExecutionError(
            command=cmd,
            returncode=result.returncode,
            stderr=result.stderr.strip(),
            stdout=result.stdout.strip(),
            message=message,
        )
    return result


def tree_sitter_version() -> str:
    result = run(["tree-sitter", "--version"])
    if result.returncode != 0:
        return "unknown"
    parts = result.stdout.strip().split()
    return parts[1] if len(parts) > 1 else "unknown"


def count_nodes(node: dict[str, Any] | None) -> int:
    if not isinstance(node, dict):
        return 0
    return 1 + sum(count_nodes(child) for child in node.get("children", []))


def has_errors(node: dict[str, Any]) -> bool:
    if node.get("type") == "ERROR":
        return True
    return any(has_errors(child) for child in node.get("children", []))


def lookup_grammar_version(grammar: str, builds_log: Path) -> str:
    if not builds_log.exists():
        return "unknown"
    latest = "unknown"
    for line in builds_log.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        try:
            entry = json.loads(line)
        except json.JSONDecodeError:
            continue
        if entry.get("grammar") == grammar:
            latest = str(entry.get("commit", "unknown"))
    return latest


def detect_compiler(grammar_dir: Path) -> str:
    if (grammar_dir / "src" / "scanner.cc").is_file():
        return "g++"
    return "gcc"


def append_build_log(layout: WorkshopLayout, grammar: str, commit: str, repo_url: str, artifact: Path, duration_ms: int) -> None:
    try:
        layout.logs_dir.mkdir(parents=True, exist_ok=True)
        entry = BuildLogEntry(
            timestamp=datetime.now(),
            grammar=grammar,
            commit=commit,
            repo_url=repo_url,
            so_path=artifact,
            build_success=True,
            build_time_ms=duration_ms,
            compiler=detect_compiler(layout.for_grammar(grammar).grammar_dir),
            tree_sitter_version=tree_sitter_version(),
        )
        with layout.builds_log.open("a", encoding="utf-8") as handle:
            handle.write(entry.model_dump_json() + "\n")
    except OSError as exc:
        raise LogWriteError(f"Failed to write build log: {exc}", path=layout.builds_log) from exc


def append_parse_log(layout: WorkshopLayout, grammar: str, source: Path, parse_output: dict[str, Any], duration_ms: int) -> None:
    try:
        layout.logs_dir.mkdir(parents=True, exist_ok=True)
        root = parse_output["root_node"]
        entry = ParseLogEntry(
            timestamp=datetime.now(),
            grammar=grammar,
            grammar_version=lookup_grammar_version(grammar, layout.builds_log),
            source_file=source,
            node_count=count_nodes(root),
            has_errors=has_errors(root),
            parse_time_ms=duration_ms,
            root_node_type=str(root.get("type", "unknown")),
        )
        with layout.parses_log.open("a", encoding="utf-8") as handle:
            handle.write(entry.model_dump_json() + "\n")
    except OSError as exc:
        raise LogWriteError(f"Failed to write parse log: {exc}", path=layout.parses_log) from exc
