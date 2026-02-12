---
name: grammar-workshop
description: Workflow for agents to create/modify/test tree-sitter grammars in Grammatic.
---

# Grammar Workshop Skill

Use this skill when the task is to build, modify, validate, or test a grammar in this repository.

## Intent

Optimize for the grammar workshop loop, not parse-centric demos.

Primary outcomes:
- grammar changes are implemented
- corpus tests are updated/passing
- doctor diagnostics are explicit and actionable
- workshop provenance includes success and failure telemetry

## Preferred Command Flow

Use Python workflow entrypoints as the canonical interface, with `just` as optional thin wrappers.

Canonical sequence for grammar `<grammar>`:
1. `python -m grammatic.workflows.generate <grammar>` (or `just generate <grammar>`)
2. `python -m grammatic.workflows.build <grammar>` (or `just build <grammar>`)
3. `python -m grammatic.workflows.test_grammar <grammar>` (or `just test-grammar <grammar>`)
4. `python -m grammatic.workflows.doctor <grammar>` (or `just doctor <grammar>`)
5. Optional spot check: `python -m grammatic.workflows.parse <grammar> <source>` (or `just parse ...`)

Grammar-name-first UX is mandatory; do not require users to pass raw grammar paths.

## Typed Contracts + Doctor Diagnostics

- Workflow request/response payloads should be typed (Pydantic models).
- Doctor output should be structured and stable (machine-readable summaries + human guidance).
- Diagnostics should identify failing stage/check, impacted grammar, and next repair step.

Keep examples concise and tied to iteration outcomes ("missing corpus test", "generate failed", "doctor check failed").

## Preflight Validation + Error Quality

Before invoking tools, validate prerequisites and fail fast with actionable messages:
- grammar directory exists under `grammars/<grammar>/`
- required sources exist (`grammar.js`, scanner/corpus files as applicable)
- command dependencies are available (`tree-sitter`, compiler toolchain)

Error messages must say:
1. what failed,
2. why it failed,
3. how to fix it with a concrete next command.

## Logging + Failure Telemetry

Workshop operations must emit structured JSONL telemetry, including failures:
- build/test/doctor events record success or failure state
- failure records include stage, error class/message, and grammar name
- parse events remain supporting telemetry for debugging

Preserve append-only logging behavior and avoid dropping failed attempts.

## Path Conventions

- Grammar root: `grammars/<grammar>/`
- Build artifact: `build/<grammar>/<grammar>.so`
- Logs: `logs/builds.jsonl`, `logs/parses.jsonl`

## MVP Scope Guardrails

Do:
- improve workshop reliability and diagnostics
- improve grammar iteration/test quality outcomes
- preserve grammar-name command contracts

Avoid:
- over-abstracting orchestration
- introducing large framework layers
- making parse workflows the primary user story
