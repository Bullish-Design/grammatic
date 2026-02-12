# CLAUDE.md
# Grammatic Development Guide

## Project Overview

Grammatic is a devenv-managed toolchain for developing, testing, and validating tree-sitter grammars. It orchestrates Unix tools (git, gcc, tree-sitter CLI, jq) via justfile targets, uses JSONL for append-only test logs, and Pydantic for type-safe data models.

**Core Philosophy:**
- Zero cross-platform abstraction (devenv provides the controlled environment)
- Compose existing tools rather than reimplementing
- Treat grammars as data (git submodules, not custom package management)
- JSONL for provenance tracking (every build and parse gets logged)
- Minimal Python (only for validation and structured logging)

## Architecture at a Glance

```
devenv.nix → justfile → {bash scripts, tree-sitter CLI, jq} → JSONL logs
                ↓
         Pydantic models validate log entries
```

**Data flow:**
1. Git submodule fetch (canonical tree-sitter grammar repos)
2. `tree-sitter generate` (grammar.js → parser.c)
3. `gcc/g++` compile (parser.c + scanner → .so shared library)
4. `tree-sitter parse --json` (source file → AST JSON)
5. Python log_writer.py (validate via Pydantic, append to JSONL)
6. `jq` queries (filter/analyze logs)

## Key Design Decisions

### Why Git Submodules?
- Grammars are already in git repos (tree-sitter-python, tree-sitter-rust, etc.)
- No need for custom package manager
- Version pinning via commit hash
- `git submodule update --remote` for updates

### Why JSONL?
- Append-only preserves complete history
- Each line = one event (build or parse)
- `jq` can stream-process without loading entire file
- Easy to export, backup, or archive

### Why Pydantic?
- Type-safe log entries catch errors at write time
- JSON schema generation for documentation
- Minimal Python footprint (models only)

### Why Justfile?
- More ergonomic than Makefiles for shell orchestration
- Better error handling (`set -euo pipefail` by default)
- Recipe dependencies and parameters

## Directory Structure Rationale

```
grammars/        # Git submodules (never manually edited)
build/           # Compiled .so files (gitignored, ephemeral)
logs/            # JSONL event logs (gitignored, exportable)
src/grammatic/   # Pydantic models only
scripts/         # Bash + UV scripts (the actual logic)
tests/fixtures/  # Sample source files for parse testing
```

**Why separate scripts/ from src/?**
- `scripts/` = executable tooling (bash, UV scripts)
- `src/` = importable Python library (Pydantic models)
- Clean separation of concerns

## Implementation Phases

### Phase 1: Foundation (MVP)
1. Create `devenv.nix` with tree-sitter, gcc, jq, git, just, uv, python
2. Create Pydantic models (`src/grammatic/models.py`)
3. Create build script (`scripts/build_grammar.py`)
4. Create log writer (`scripts/log_writer.py`)
5. Create justfile with core targets (init, add-grammar, build, parse)

### Phase 2: Testing & Validation
1. Add grammar corpus test runner (`just test-grammar`)
2. Add log validation (`just validate-logs`)
3. Create fixture files for integration tests
4. Add pre-commit hooks for JSONL validation

### Phase 3: Querying & Analysis
1. Add jq-based log query targets
2. Add metrics computation (avg parse time, success rate)
3. Add log export functionality

### Phase 4: Developer Experience
1. Add watch mode for iterative development
2. Add grammar template generator
3. Add comprehensive error messages
4. Document common workflows

## Critical Implementation Details

### Build Script Concerns

**Scanner detection:**
- Check for `scanner.cc` → use `g++`
- Check for `scanner.c` → use `gcc`
- No scanner → use `gcc` for parser only

**Platform-specific flags:**
- Linux: `-shared`
- macOS: `-dynamiclib`

**Always include:** `-fPIC -O2 -I<grammar_dir>/src`

### Log Writer Concerns

**Build events:**
- Extract commit hash: `git -C grammars/<name> rev-parse HEAD`
- Extract remote URL: `git -C grammars/<name> config --get remote.origin.url`
- Detect compiler from scanner file presence
- Measure build time in milliseconds

**Parse events:**
- Count nodes recursively in AST JSON
- Detect errors by searching for `"type": "ERROR"` nodes
- Lookup grammar version from most recent build log entry
- Handle missing builds.jsonl gracefully (version = "unknown")

### Justfile Best Practices

**Always use bash with strict mode:**
```makefile
set shell := ["bash", "-euo", "pipefail", "-c"]
```

**For targets with bash scripts:**
```makefile
build GRAMMAR:
    #!/usr/bin/env bash
    # script here
```

**Avoid silent failures:** Capture exit codes, check file existence before operations

## Testing Strategy

### Grammar Corpus Tests
Tree-sitter's native test format in `test/corpus/*.txt`:
- Input source code
- Expected AST structure
- Run via `tree-sitter test` in grammar directory

### Integration Tests
- Fixture files in `tests/fixtures/`
- Parse with built grammar
- Verify zero ERROR nodes for valid input
- Verify log entries created correctly

### Log Validation
- Pre-commit hook runs `jq -e '.' logs/*.jsonl`
- Ensures every line is valid JSON
- Catches malformed log entries before commit

## Common Workflows

### Adding Official Grammar
```bash
just add-grammar python https://github.com/tree-sitter/tree-sitter-python
just generate python
just build python
just test-grammar python
```

### Developing Custom Grammar
```bash
just new-grammar mylang
# Edit grammars/mylang/grammar.js
# Add tests to grammars/mylang/test/corpus/
just watch mylang  # Iterative development
```

### Analyzing Parse Performance
```bash
just query-parses-for python
just avg-parse-time python
just query-failures  # Find problematic inputs
```

## Error Handling Patterns

### In Bash Scripts
```bash
# Validate before acting
if [ ! -f "path/to/file" ]; then
    echo "Error: file not found" >&2
    exit 1
fi

# Capture and check exit codes
if ! command_that_might_fail; then
    echo "Error: command failed" >&2
    exit 1
fi
```

### In Python Log Writer
```python
# Use Pydantic validation
try:
    entry = BuildLogEntry(...)
except ValidationError as e:
    print(f"Invalid log entry: {e}", file=sys.stderr)
    sys.exit(1)

# Graceful degradation for missing data
grammar_version = "unknown"
try:
    # attempt to lookup
except Exception as e:
    print(f"Warning: {e}", file=sys.stderr)
```

## Skills Reference

Before implementing tree-sitter-specific functionality, consult the tree-sitter grammar development skill for workflow patterns and best practices.

## Known Constraints

### No Windows Support (MVP)
- Relies on Unix-specific bash features
- Shared library compilation flags differ on Windows
- Future: Add MSVC/MinGW support

### Non-Atomic Log Writes
- JSONL appends not atomic (no file locking)
- Parallel builds could corrupt logs
- Mitigation: Run builds sequentially via justfile dependencies
- Future: Migrate to SQLite

### No Semantic Versioning
- Grammars versioned by git commit hash only
- No compatibility tracking between grammar versions
- Future: Add compatibility matrix

## Next Steps for Implementation

1. **Start with devenv.nix** - Get the environment right first
2. **Create Pydantic models** - Define the data structures
3. **Build the build script** - Core functionality for compilation
4. **Create minimal justfile** - Just `init`, `build`, `parse`
5. **Add log writer** - Enable JSONL event tracking
6. **Test with Python grammar** - Validate the whole pipeline
7. **Add query targets** - Make logs useful
8. **Iterate on UX** - Watch mode, templates, better errors

## Success Criteria

The MVP is complete when:
- Python grammar can be added, built, and tested
- Build and parse events logged to JSONL
- Logs queryable via jq-based justfile targets
- Zero ERROR nodes when parsing valid Python
- Log export produces valid tarball

## References

- Tree-sitter docs: https://tree-sitter.github.io/tree-sitter/
- Justfile manual: https://just.systems/man/en/
- Pydantic docs: https://docs.pydantic.dev/
- jq manual: https://jqlang.github.io/jq/manual/
