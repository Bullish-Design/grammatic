# Grammatic Concept

Grammatic is a **grammar workshop** for humans and agents.

It is not primarily a parser wrapper. Parsing support exists, but the core value is enabling fast, reliable cycles for **creating, modifying, validating, and testing tree-sitter grammars**.

---

## Core Idea

Use existing Unix tools as-is, coordinate them with `just`, and record outcomes in append-only JSONL logs.

- **Control plane:** `just`
- **Grammar engine:** `tree-sitter` CLI
- **Build toolchain:** `gcc` / `g++`
- **Validation + logging:** small Python scripts with Pydantic
- **Querying:** `jq`

Grammatic should stay shell-first, explicit, and deterministic.

---

## Workshop Loop (Primary Workflow)

The workshop loop is:

1. **Create / modify grammar** (`grammar.js`, scanner, corpus tests)
2. **Generate** parser artifacts
3. **Build** shared library
4. **Test** corpus behavior
5. **Diagnose** issues and iterate

This loop is the product.

Parsing individual files is a supporting tool for debugging and spot checks, not the main success criterion.

---

## Command Contract

The core interface is grammar-name based:

- `just generate <grammar>`
- `just build <grammar>`
- `just test-grammar <grammar>`
- `just doctor <grammar>`
- `just parse <grammar> <source>` (auxiliary)

Recipes should resolve paths internally from project root + grammar name.

---

## Artifact Contract

Build output is organized per grammar:

- `build/<grammar>/<grammar>.so`

This layout is canonical and should be used consistently across scripts, checks, and docs.

---


## Workflow Architecture

Python command handlers are the source of truth for workflow behavior:

- `generate`
- `build`
- `test-grammar`
- `doctor`
- `parse`

`just` recipes are delegation-only wrappers. They should forward grammar-name arguments to Python entrypoints and should not duplicate validation, error mapping, or orchestration logic.

### Uniform Exceptions and Exit Codes

Handlers should share a uniform exception taxonomy with stable exit code mapping.

- identical failure category => identical process exit code
- command-specific context is fine, but code mapping must remain stable
- delegating `just` recipes should preserve the Python process exit code

### Consistent Preflight Contracts

Each handler should run consistent prerequisite checks before invoking external tools, based on command needs:

- grammar exists: `grammars/<grammar>/`
- generated parser exists when required by the workflow stage
- corpus tests exist for test/diagnostic flows
- build artifact exists when required: `build/<grammar>/<grammar>.so`

### Grammar-Name-First Examples

```bash
just generate python
just build python
just test-grammar python
just doctor python
just parse python tests/fixtures/sample_python.py
```

Canonical shared-library output remains:

```text
build/python/python.so
```

## Testing-First Philosophy

Testing is central, not optional:

- Corpus tests (`tree-sitter test`) are first-class
- `doctor` checks catch common setup/quality issues quickly
- Parse commands provide supplemental diagnostics

Primary indicator of grammar health: **test results + diagnostics**, not parse demos.

---

## Provenance Model

Workshop provenance is recorded as **append-only JSONL** events. Every workflow run must append an event for both **success and failure** outcomes to preserve a complete audit trail for grammar iteration.

Required event fields:

- `event_type`
- `timestamp`
- `grammar`
- `status`
- `duration_ms`

Optional diagnostics (recommended on failures, allowed on successes where relevant):

- `error_code`
- `stderr_excerpt`

Build events and parse telemetry are intentionally distinct:

- **Build events** are first-class provenance records for generate/build/test/doctor outcomes and are the primary iteration history.
- **Parse telemetry** is supportive diagnostic data for spot validation and should not be treated as the primary quality signal.

Canonical event schema definitions must live in `src/grammatic/models.py` (or a successor contract module that replaces it). Runtime logging code should validate against these Pydantic models before appending to JSONL.

Example successful build event:

```json
{"event_type":"build","timestamp":"2026-01-15T10:20:30Z","grammar":"python","status":"success","duration_ms":912}
```

Example failed build event:

```json
{"event_type":"build","timestamp":"2026-01-15T10:21:02Z","grammar":"python","status":"failure","duration_ms":487,"error_code":"gcc_compile_failed","stderr_excerpt":"cc1plus: fatal error: scanner.cc: No such file or directory"}
```

---

## Scope Boundaries (MVP)

In scope:

- grammar workshop loop
- grammar-name command UX
- deterministic build layout
- test-first flows
- lightweight structured logs

Out of scope for now:

- complex API/version governance
- heavy orchestration frameworks
- platform abstraction beyond devenv-controlled Unix workflow
- replacing tree-sitter functionality with custom implementations

---

## Success Definition

Grammatic succeeds when humans and agents can quickly improve grammars with predictable feedback:

- edit grammar
- regenerate and rebuild
- run corpus tests
- diagnose failures
- repeat with clear provenance
