# Phase 1: Foundation & Data Models

## Scope
Establish project structure, environment configuration, and type-safe data models. This phase has zero runtime dependencies on other components.

## Deliverables

### 1. Environment Configuration

**File: `devenv.nix`**
```nix
{ pkgs, ... }:

{
  packages = with pkgs; [
    tree-sitter
    gcc
    gnumake
    python312
    uv
    jq
    git
    just
    watchexec
  ];
  
  languages.python = {
    enable = true;
    package = pkgs.python312;
  };
  
  env = {
    GRAMMATIC_ROOT = builtins.toString ./.;
  };
  
  enterShell = ''
    echo "Grammatic development environment loaded"
    mkdir -p logs build grammars tests/fixtures schemas
  '';
}
```

**File: `pyproject.toml`**
```toml
[project]
name = "grammatic"
version = "0.1.0"
description = "Tree-sitter grammar development toolchain"
requires-python = ">=3.12"
dependencies = [
    "pydantic>=2.0",
]

[project.optional-dependencies]
dev = [
    "pytest>=8.0",
    "pytest-cov>=4.0",
]

[tool.uv]
dev-dependencies = [
    "pytest>=8.0",
    "pytest-cov>=4.0",
]

[tool.ruff]
line-length = 120
target-version = "py312"

[tool.ruff.lint]
select = ["E", "F", "I"]
```

### 2. Data Models

**File: `src/grammatic/__init__.py`**
```python
# src/grammatic/__init__.py
from __future__ import annotations

from grammatic.models import BuildLogEntry, GrammarMetadata, ParseLogEntry

__all__ = ["BuildLogEntry", "ParseLogEntry", "GrammarMetadata"]
```

**File: `src/grammatic/models.py`**
```python
# src/grammatic/models.py
from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, Field


class BuildLogEntry(BaseModel):
    """Build event metadata for JSONL log."""

    event_type: Literal["build"] = Field(default="build")
    timestamp: datetime
    grammar: str
    commit: str
    repo_url: str
    so_path: Path
    build_success: bool
    build_time_ms: int
    compiler: Literal["gcc", "g++"]
    tree_sitter_version: str


class ParseLogEntry(BaseModel):
    """Parse test result metadata for JSONL log."""

    event_type: Literal["parse"] = Field(default="parse")
    timestamp: datetime
    grammar: str
    grammar_version: str
    source_file: Path
    node_count: int
    has_errors: bool
    parse_time_ms: int
    root_node_type: str


class GrammarMetadata(BaseModel):
    """Runtime metadata about grammar state."""

    name: str
    submodule_path: Path
    current_commit: str
    remote_url: str
    last_build_timestamp: datetime | None
    so_exists: bool
```

### 3. Directory Structure

**File: `.gitignore`**
```
# Build artifacts
build/
*.so

# Logs
logs/
*.jsonl

# Python
__pycache__/
*.py[cod]
*$py.class
.pytest_cache/
.coverage
htmlcov/

# UV
.venv/

# Devenv
.devenv/
.devenv.flake.nix

# Temp files
/tmp/
*.tmp
```

**File: `README.md`**
```markdown
# Grammatic

Tree-sitter grammar development toolchain using devenv, justfile, and JSONL logs.

## Quick Start

```bash
# Enter devenv shell
devenv shell

# Initialize workspace
just init

# Add a grammar
just add-grammar python https://github.com/tree-sitter/tree-sitter-python

# Build and test
just generate python
just build python
just parse python tests/fixtures/sample.py
```

## Documentation

See [CLAUDE.md](CLAUDE.md) for development guide.
See [Grammatic_Summary.md](src/docs/Grammatic_Summary.md) for architecture overview.
```

## Verification Tests

**File: `tests/test_models.py`**
```python
# tests/test_models.py
from __future__ import annotations

from datetime import datetime
from pathlib import Path

import pytest
from pydantic import ValidationError

from grammatic.models import BuildLogEntry, GrammarMetadata, ParseLogEntry


class TestBuildLogEntry:
    def test_valid_entry(self):
        entry = BuildLogEntry(
            timestamp=datetime.now(),
            grammar="python",
            commit="abc123",
            repo_url="https://github.com/tree-sitter/tree-sitter-python",
            so_path=Path("build/python.so"),
            build_success=True,
            build_time_ms=1234,
            compiler="gcc",
            tree_sitter_version="0.21.0",
        )
        assert entry.event_type == "build"
        assert entry.grammar == "python"

    def test_invalid_compiler(self):
        with pytest.raises(ValidationError):
            BuildLogEntry(
                timestamp=datetime.now(),
                grammar="python",
                commit="abc123",
                repo_url="https://github.com/tree-sitter/tree-sitter-python",
                so_path=Path("build/python.so"),
                build_success=True,
                build_time_ms=1234,
                compiler="clang",  # Invalid
                tree_sitter_version="0.21.0",
            )

    def test_json_serialization(self):
        entry = BuildLogEntry(
            timestamp=datetime(2026, 2, 10, 15, 30, 45),
            grammar="python",
            commit="abc123",
            repo_url="https://github.com/tree-sitter/tree-sitter-python",
            so_path=Path("build/python.so"),
            build_success=True,
            build_time_ms=1234,
            compiler="gcc",
            tree_sitter_version="0.21.0",
        )
        json_str = entry.model_dump_json()
        assert "python" in json_str
        assert "abc123" in json_str


class TestParseLogEntry:
    def test_valid_entry(self):
        entry = ParseLogEntry(
            timestamp=datetime.now(),
            grammar="python",
            grammar_version="abc123",
            source_file=Path("test.py"),
            node_count=42,
            has_errors=False,
            parse_time_ms=12,
            root_node_type="module",
        )
        assert entry.event_type == "parse"
        assert entry.has_errors is False

    def test_with_errors(self):
        entry = ParseLogEntry(
            timestamp=datetime.now(),
            grammar="python",
            grammar_version="abc123",
            source_file=Path("test.py"),
            node_count=42,
            has_errors=True,
            parse_time_ms=12,
            root_node_type="ERROR",
        )
        assert entry.has_errors is True

    def test_json_serialization(self):
        entry = ParseLogEntry(
            timestamp=datetime(2026, 2, 10, 15, 31, 12),
            grammar="python",
            grammar_version="abc123",
            source_file=Path("test.py"),
            node_count=42,
            has_errors=False,
            parse_time_ms=12,
            root_node_type="module",
        )
        json_str = entry.model_dump_json()
        assert "parse" in json_str
        assert "module" in json_str


class TestGrammarMetadata:
    def test_valid_metadata(self):
        meta = GrammarMetadata(
            name="python",
            submodule_path=Path("grammars/python"),
            current_commit="abc123",
            remote_url="https://github.com/tree-sitter/tree-sitter-python",
            last_build_timestamp=datetime.now(),
            so_exists=True,
        )
        assert meta.name == "python"
        assert meta.so_exists is True

    def test_no_build_yet(self):
        meta = GrammarMetadata(
            name="python",
            submodule_path=Path("grammars/python"),
            current_commit="abc123",
            remote_url="https://github.com/tree-sitter/tree-sitter-python",
            last_build_timestamp=None,
            so_exists=False,
        )
        assert meta.last_build_timestamp is None
```

## Acceptance Criteria

- [ ] `devenv shell` successfully loads environment
- [ ] All packages (tree-sitter, gcc, jq, etc.) available in PATH
- [ ] Pydantic models import without errors
- [ ] All model tests pass (`pytest tests/test_models.py`)
- [ ] JSON serialization/deserialization works for all models
- [ ] Invalid data raises ValidationError appropriately
- [ ] Directory structure created on shell entry

## Run Tests

```bash
devenv shell
uv pip install -e ".[dev]"
pytest tests/test_models.py -v
```
