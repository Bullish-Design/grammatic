# Python Orchestration Migration Guide

This guide explains how to migrate workflow behavior from `justfile` recipes into Python orchestration modules while preserving the existing CLI UX.

## Responsibility Split: `justfile` vs Python Modules

### Keep in `justfile`

`just` remains a thin command surface and should focus on:

- command aliases and discoverable task names
- forwarding grammar-name-first arguments to Python entrypoints
- setting up shell-friendly invocation defaults
- preserving and returning Python process exit codes

`justfile` recipes should **not** duplicate validation, orchestration, or logging logic that belongs in Python.

### Move to Python modules

Python modules are the source of truth for workflow behavior and should own:

- grammar-name to canonical path resolution from repo root
- preflight validation (required dirs/files/tools)
- subprocess orchestration (`tree-sitter`, compiler, `jq`, etc.)
- typed request/result contracts (Pydantic models)
- success/failure event logging to append-only JSONL streams
- stable exception-to-exit-code mapping and actionable diagnostics

## Recipe Migration Checklist

Use this checklist when migrating any existing `just` recipe:

1. **Identify recipe inputs and outputs**
   - enumerate all recipe arguments and expected artifacts
   - define a typed request model and typed result model

2. **Extract validations into Python**
   - move path/tool checks out of shell conditionals
   - normalize grammar-name-first inputs to canonical paths
   - emit consistent, actionable validation errors

3. **Extract subprocess calls into Python orchestration**
   - move command composition and execution into Python handlers
   - capture stdout/stderr/exit status in a structured way
   - preserve deterministic artifact paths

4. **Adopt typed contracts**
   - implement Pydantic request/result models for handler boundaries
   - include fields needed by command output and logging

5. **Add/align log emission**
   - append workflow events to the correct JSONL log
   - write entries for both success and failure outcomes
   - include status, timing, and diagnostic fields where relevant

6. **Update tests**
   - add/update unit tests for validation and error taxonomy
   - add/update integration tests for command behavior and artifacts
   - assert that both success and failure paths emit logs

7. **Thin the `just` recipe**
   - replace inline logic with a direct Python entrypoint call
   - keep command name and argument shape stable

## Backward Compatibility for `just` Commands

Migration must preserve existing command discoverability and behavior:

- keep existing `just` command names stable (`generate`, `build`, `test-grammar`, `doctor`, `parse`, etc.)
- preserve grammar-name-first invocation patterns
- maintain argument ordering and defaults unless a documented breaking change is approved
- preserve expected artifacts at canonical locations
- keep stable exit semantics by preserving Python exit codes through `just`

Any behavior changes should be additive and documented in `README.md` and relevant command help text.

## Definition of Done (DoD)

A recipe migration is complete only when all criteria below are met:

- **Typed contracts**
  - request/result models exist for the migrated workflow boundary
  - model validation covers required inputs and key invariants

- **Consistent errors**
  - validation and runtime failures use the shared error taxonomy
  - diagnostics are actionable and map to stable exit codes

- **Success/failure logging**
  - both successful and failed runs append structured events
  - required fields are present and timestamps/duration are populated

- **Tests updated**
  - relevant unit/integration tests are added or revised
  - tests cover happy path, validation failure, and tool/subprocess failure
  - tests verify log emission behavior for both outcomes
