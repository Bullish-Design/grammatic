# Grammatic

Grammatic is a **tree-sitter grammar workshop** for humans and agents.

It provides a shell-first workflow for creating, modifying, validating, and testing grammars using existing tools (`tree-sitter`, `gcc/g++`, `jq`, `git`) coordinated through `just`.

## Why Grammatic

Grammatic is intentionally lightweight:

- `just` as the control plane
- tree-sitter CLI for generation, testing, and parse capabilities
- small Python scripts for typed logging and validation
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

Workflow orchestration lives in Python command handlers and is the source of truth for command behavior:

- `generate`
- `build`
- `test-grammar`
- `doctor`
- `parse`

`just` recipes are thin delegators. They should pass grammar-name-first inputs to Python entrypoints and avoid duplicating orchestration logic.

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

If pytest reports environment/setup errors rather than assertion failures, check tool availability first:

```bash
just --version
tree-sitter --version
pytest -rs
```

Many integration-style tests are intentionally skipped when `just` or `tree-sitter` is missing, and this can mask repository-layout issues until runtime.

The `grammatic.workspace` Pydantic models can be used in scripts to validate repository and grammar paths early, so failures become actionable before shell commands run.

## Additional Documentation

- [CONCEPT.md](./CONCEPT.md) — distilled project concept and scope
- [AGENTS.md](./AGENTS.md) — agent operating guidance
- [docs/migration/python-orchestration.md](./docs/migration/python-orchestration.md) — migration guide for moving recipe orchestration from `just` into Python modules
- [skills/grammar-workshop/SKILL.md](./skills/grammar-workshop/SKILL.md) — reusable agent workflow skill
- [skills/query-workshop/SKILL.md](./skills/query-workshop/SKILL.md) — reusable workflow for tree-sitter query (`.scm`) authoring and evaluation
