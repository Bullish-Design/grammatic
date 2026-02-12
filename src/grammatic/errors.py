from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(slots=True)
class GrammaticError(Exception):
    """Base typed error for stable CLI diagnostics and exit-code mapping."""

    message: str

    def __str__(self) -> str:
        return self.message


class ValidationError(GrammaticError):
    """Workspace/input invariant failures."""


class ToolMissingError(GrammaticError):
    """Raised when an expected tool binary is unavailable."""


@dataclass(slots=True)
class SubprocessExecutionError(GrammaticError):
    """Raised when a subprocess command fails."""

    command: list[str]
    returncode: int
    stderr: str = ""
    stdout: str = ""

    def __init__(self, *, command: list[str], returncode: int, stderr: str = "", stdout: str = "", message: str | None = None):
        self.command = command
        self.returncode = returncode
        self.stderr = stderr
        self.stdout = stdout
        super().__init__(message or f"Command failed ({returncode}): {' '.join(command)}")


class ArtifactMissingError(GrammaticError):
    """Raised when an expected generated artifact is missing."""


@dataclass(slots=True)
class LogWriteError(GrammaticError):
    """Raised when read/write access for structured logs fails."""

    path: Path

    def __init__(self, message: str, path: Path):
        self.path = path
        super().__init__(message)
