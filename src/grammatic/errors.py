from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


SUBPROCESS_EXCERPT_LIMIT = 800


def bounded_output_excerpt(stderr: str, stdout: str, *, limit: int = SUBPROCESS_EXCERPT_LIMIT) -> str:
    """Return a bounded stderr excerpt, falling back to stdout when needed."""
    text = (stderr or stdout or "").strip()
    if len(text) <= limit:
        return text
    return f"{text[:limit].rstrip()}…"


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


class SubprocessExecutionError(GrammaticError):
    """Raised when a subprocess command fails."""

    def __init__(self, *, command: list[str], returncode: int, stderr: str = "", stdout: str = "", message: str | None = None):
        self.command = command
        self.returncode = returncode
        self.stderr = stderr
        self.stdout = stdout
        cmd_text = " ".join(command)
        excerpt = bounded_output_excerpt(stderr, stdout)
        detail = f"command={cmd_text}; return_code={returncode}"
        if excerpt:
            detail += f"; output={excerpt}"
        prefix = message or "Subprocess command failed"
        super().__init__(message=f"{prefix}. {detail}")

    def excerpt(self, *, limit: int = SUBPROCESS_EXCERPT_LIMIT) -> str:
        return bounded_output_excerpt(self.stderr, self.stdout, limit=limit)


class ArtifactMissingError(GrammaticError):
    """Raised when an expected generated artifact is missing."""


@dataclass(slots=True)
class LogWriteError(GrammaticError):
    """Raised when read/write access for structured logs fails."""

    path: Path

    def __init__(self, message: str, path: Path):
        self.path = path
        super().__init__(message)
