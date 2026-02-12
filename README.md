# Grammatic

Grammatic is a **tree-sitter grammar workshop** for humans and agents.

It provides a Python-first workflow for creating, modifying, validating, and testing grammars using existing tools (`tree-sitter`, `gcc/g++`, `git`).

## Why Grammatic

Grammatic is intentionally lightweight:

- Python workflows with typed contracts (Pydantic models)
- `just` as a convenient command surface (thin wrappers around Python)
- tree-sitter CLI for generation, testing, and parse capabilities
- append-only JSONL logs for reproducible workshop history

Primary goal: **fast grammar iteration with strong testing feedback**.

## Core Workflow

```bash
just init
just add-grammar python https://github.com/tree-sitter/tree-sitter-python

# iterate on grammar + corpus tests
just generate python
just build python
just test-grammar python
just doctor python
```

Use parse as a supporting check when needed:

```bash
just parse python tests/fixtures/sample_python.py
```

## Command Surface (MVP)

All key commands are grammar-name based:

- `just generate <grammar>`
- `just build <grammar>`
- `just test-grammar <grammar>`
- `just doctor <grammar>`
- `just parse <grammar> <source>` (auxiliary)
- `just query-*` and metrics helpers for logs

## Canonical Paths

- Grammar sources: `grammars/<grammar>/`
- Build outputs: `build/<grammar>/<grammar>.so`
- Logs: `logs/builds.jsonl`, `logs/parses.jsonl`

## Workflow Architecture

All workflow orchestration lives in **Python modules** (`src/grammatic/workflows/`):

- `handle_generate()` - Generate parser from grammar.js
- `handle_build()` - Compile grammar to .so library
- `handle_test_grammar()` - Run corpus tests
- `handle_doctor()` - Diagnostic checks
- `handle_parse()` - Parse source files

`just` recipes are thin wrappers that call the Python CLI (`src/grammatic/cli/__main__.py`), which delegates to these workflow handlers. All logic, validation, and logging happens in Python.

## Developer UX Principles

- Every workflow command should have a typed request object and typed result object.
- Validation should be centralized in model validators and path services, not duplicated in shell snippets.
- The CLI layer should only parse arguments and render errors/results.
- The test strategy should map directly to model behavior and workflow behavior.

| Operation | Typed request contract | Typed result contract |
| --- | --- | --- |
| `build` | `BuildRequest` (grammar name, workspace/build context) | `BuildResult` (status, artifact path, diagnostics, duration) |
| `parse` | `ParseRequest` (grammar name, source path/content mode) | `ParseResult` (status, tree/output summary, diagnostics, duration) |
| `doctor` | `DoctorRequest` (grammar name, checks/profile options) | `DoctorResult` (status, findings, recommendations, duration) |
| `test-grammar` | `TestGrammarRequest` (grammar name, corpus/test options) | `TestGrammarResult` (status, pass/fail counts, diagnostics, duration) |

### Command and Exit Semantics

Python handlers should implement a uniform exception taxonomy that maps to stable exit codes across commands.

- Same error class => same exit code, regardless of command
- Actionable diagnostics should be emitted consistently
- Shell wrappers should preserve Python exit codes

### Shared Preflight Checks

Before tool invocation, handlers should run consistent preflight checks where applicable:

- grammar exists: `grammars/<grammar>/`
- generated parser exists (for build/test/doctor/parse flows)
- corpus exists (for test/doctor flows)
- canonical build artifact exists when required: `build/<grammar>/<grammar>.so`

### Concrete Grammar-Name Examples

Generate and build a grammar by name:

```bash
just generate python
just build python
```

Canonical build output path:

```text
build/python/python.so
```

Validate and diagnose the same grammar using the same name-based interface:

```bash
just test-grammar python
just doctor python
just parse python tests/fixtures/sample_python.py
```

## Testing-First Orientation

Testing is the center of the project:

- corpus tests (`tree-sitter test`) are first-class
- `doctor` identifies common grammar setup/quality issues
- parse output is useful but secondary to test outcomes

## Provenance Model

Grammatic uses append-only JSONL logs for workshop provenance. Every relevant workflow execution must append an event for both successful and failed outcomes.

Required fields for each event:

- `event_type`
- `timestamp`
- `grammar`
- `status`
- `duration_ms`

Optional diagnostics (especially for failures):

- `error_code`
- `stderr_excerpt`

Build and parse records serve different purposes:

- **Build events** are the primary provenance stream and should capture outcome status for workshop iteration.
- **Parse telemetry** is secondary support data for spot checks and diagnostics.

Canonical event schemas should be defined with Pydantic in `src/grammatic/models.py` (or a successor contract module if schemas are relocated).

Successful build event example:

```json
{"event_type":"build","timestamp":"2026-01-15T10:20:30Z","grammar":"python","status":"success","duration_ms":912}
```

Failed build event example:

```json
{"event_type":"build","timestamp":"2026-01-15T10:21:02Z","grammar":"python","status":"failure","duration_ms":487,"error_code":"gcc_compile_failed","stderr_excerpt":"cc1plus: fatal error: scanner.cc: No such file or directory"}
```

## Development Environment

Use the devenv-managed environment for consistent tooling:

```bash
devenv shell
```

The canonical runtime is Python 3.13 + `uv`, with `just`, `tree-sitter`, compilers, and `jq` available.


## Pytest Troubleshooting

If pytest reports environment/setup errors rather than assertion failures, run the import preflight first so missing package setup fails once with an actionable message:

```bash
just preflight-import
```

Then check tool availability:

```bash
just --version
tree-sitter --version
pytest -rs
```

Many integration-style tests are intentionally skipped when `just` or `tree-sitter` is missing, and this can mask repository-layout issues until runtime.

The `grammatic.workspace` Pydantic models can be used in scripts to validate repository and grammar paths early, so failures become actionable before shell commands run.

## Python API Usage

You can also use the Python API directly without `just`:

```python
from pathlib import Path
from grammatic.contracts import BuildRequest, ParseRequest
from grammatic.workflows import handle_build, handle_parse

# Build a grammar
result = handle_build(BuildRequest(
    grammar="python",
    repo_root=Path("/path/to/grammatic")
))

# Parse a file
result = handle_parse(ParseRequest(
    grammar="python",
    repo_root=Path("/path/to/grammatic"),
    source=Path("test.py")
))
```

## Additional Documentation

- [CONCEPT.md](./CONCEPT.md) — distilled project concept and scope
- [AGENTS.md](./AGENTS.md) — agent operating guidance
- [skills/grammar-workshop/SKILL.md](./skills/grammar-workshop/SKILL.md) — reusable agent workflow skill
- [skills/query-workshop/SKILL.md](./skills/query-workshop/SKILL.md) — reusable workflow for tree-sitter query (`.scm`) authoring and evaluation
