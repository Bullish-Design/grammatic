from __future__ import annotations

import json
import shutil
import subprocess
import time
from pathlib import Path
from typing import Any

from grammatic.errors import SubprocessExecutionError, ToolMissingError


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


