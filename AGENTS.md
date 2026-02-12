# Grammatic Agent Guide

This file defines how agents should operate in this repository.

## Project Positioning

Grammatic is a **tree-sitter grammar workshop**.

Focus on:
- creating grammars
- modifying grammars
- validating grammars
- testing grammars

Parsing exists, but is secondary to grammar iteration and test quality.

## Core Principles

1. **Use existing tools**
   - Prefer `tree-sitter`, `gcc/g++`, `git` for core functionality
   - Do not reimplement tree-sitter capabilities in Python

2. **Python-first architecture**
   - All workflow orchestration lives in Python modules (`src/grammatic/workflows/`)
   - `just` provides a convenient command surface as thin wrappers
   - All validation, logging, and business logic in Python with typed contracts
   - Tests should use Python APIs directly, not shell commands

3. **Grammar-name-first UX**
   - Commands should be invoked with grammar names (not raw paths)
   - Grammar-name-first UX is mandatory; path resolution happens in Python from repo root

4. **Testing is primary**
   - Corpus tests are first-class
   - Grammar quality is measured by test outcomes and diagnostics

5. **Structured provenance**
   - Keep append-only JSONL logs for workshop events
   - Pydantic models are required for workflow request/response contracts and event logging

## Developer UX Principles

- Every workflow command has a typed request object and typed result object.
- Validation is centralized in model validators/path services, not duplicated in shell snippets.
- CLI layer only parses args and renders errors/results.
- Test strategy maps directly to model and workflow behavior.

| Operation | Typed request contract | Typed result contract |
| --- | --- | --- |
| `build` | `BuildRequest` (grammar identity + workspace/build context) | `BuildResult` (status, artifact location, diagnostics, duration) |
| `parse` | `ParseRequest` (grammar identity + source input) | `ParseResult` (status, parse summary/tree output, diagnostics, duration) |
| `doctor` | `DoctorRequest` (grammar identity + check profile/options) | `DoctorResult` (status, findings, recommendations, duration) |
| `test-grammar` | `TestGrammarRequest` (grammar identity + corpus/test options) | `TestGrammarResult` (status, pass/fail counts, diagnostics, duration) |

## Canonical Workflow

Use this loop as the default process:

1. Add/create grammar (`just add-grammar` or `just new-grammar`)
2. Edit grammar sources and corpus tests
3. `just generate <grammar>` → calls `handle_generate()`
4. `just build <grammar>` → calls `handle_build()`
5. `just test-grammar <grammar>` → calls `handle_test_grammar()`
6. `just doctor <grammar>` → calls `handle_doctor()`
7. Optional: `just parse <grammar> <source>` → calls `handle_parse()`
8. Inspect logs using `LogRepository` or CLI commands
9. Iterate

All workflow handlers are in `src/grammatic/workflows/` and can be called directly from Python code.

## Path + Artifact Conventions

- Grammar sources: `grammars/<grammar>/...`
- Build outputs: `build/<grammar>/<grammar>.so` (canonical)
- Logs: `logs/builds.jsonl`, `logs/parses.jsonl`

Agents should preserve these conventions when making changes.

## Logging Expectations

- Build events should include success/failure state
- Parse events are supporting telemetry
- Prefer minimal-but-useful fields over large schemas
- Include agent/run metadata when practical

## Implementation Guidance

- Prioritize reliability and clarity over abstraction
- Fail loudly with actionable error messages
- Validate file/dir prerequisites before running tool commands
- **All workflow logic lives in Python modules** (`src/grammatic/workflows/`)
- Use Pydantic models for all request/result contracts and event logs
- `just` is a thin convenience layer only - no logic in justfile
- Python handles all grammar-name to path resolution
- Tests use Python APIs directly, not subprocess calls to `just`

## Scope for MVP

Prioritize:
- workshop loop quality (generate/build/test/doctor)
- grammar-name command consistency
- deterministic build layout
- useful provenance

De-prioritize:
- broad platform support beyond the devenv Unix environment
- complex architectural layers
- over-designed APIs

## Useful Documents

- [CONCEPT.md](./CONCEPT.md): core concept and scope
- [README.md](./README.md): user-facing quick start and workflows
- [skills/grammar-workshop/SKILL.md](./skills/grammar-workshop/SKILL.md): recommended agent workflow skill
- [skills/query-workshop/SKILL.md](./skills/query-workshop/SKILL.md): recommended agent workflow skill for tree-sitter query (.scm) authoring
