---
name: query-workshop
description: Workflow for agents to create, modify, and evaluate tree-sitter .scm query files for grammars in Grammatic.
---

# Query Workshop Skill

Use this skill when the task is to add, update, validate, or review tree-sitter query files (`.scm`) for a grammar in this repository.

## Intent

Optimize for high-signal query behavior that improves grammar usability while preserving the grammar workshop loop.

Primary outcomes:
- captures align with real syntax nodes
- query behavior is verified on representative fixtures
- diagnostics clearly explain failures and next actions
- logging captures both successful runs and failure telemetry

## Preferred Command Flow

Run grammar workflows through Python entrypoints first; `just` remains an optional convenience wrapper.

For grammar `<grammar>`:
1. `python -m grammatic.workflows.generate <grammar>` (or `just generate <grammar>`)
2. `python -m grammatic.workflows.build <grammar>` (or `just build <grammar>`)
3. `python -m grammatic.workflows.test_grammar <grammar>` (or `just test-grammar <grammar>`)
4. `python -m grammatic.workflows.doctor <grammar>` (or `just doctor <grammar>`)
5. Apply/update query files and validate with `tree-sitter query`
6. Optional focused parse check: `python -m grammatic.workflows.parse <grammar> <source>`

Always keep grammar-name-first UX; avoid raw path-centric command interfaces.

## Typed Contracts + Structured Diagnostics

- Workflow inputs/outputs should use typed models (Pydantic) for reproducible automation.
- Doctor diagnostics should be structured (check id/status/severity/message/remediation).
- Query validation output should map failures to concrete patterns/captures when possible.

Keep diagnostics concise and directly useful for iteration on grammar + tests.

## Preflight Validation + Actionable Errors

Before query evaluation, validate:
- grammar exists at `grammars/<grammar>/`
- query files exist in expected locations (for example `queries/highlights.scm`)
- grammar build artifacts/tooling prerequisites are available

Failures should state what is missing, why it matters, and the next command to recover.

## Logging + Failure Telemetry

Record structured workshop events for query operations and prerequisite grammar workflow steps:
- include operation type, grammar name, timestamps, and outcome
- explicitly log failures with stage/check and error details
- keep append-only JSONL provenance so failed attempts are preserved for debugging

## Query Authoring Guidelines

- Start from concrete node names from grammar + corpus outputs.
- Prefer specific patterns before broad alternations.
- Use stable, intention-revealing capture names.
- Avoid wildcard-heavy patterns that hide regressions.
- Re-run grammar tests/doctor after meaningful query changes.

## Concise Iteration Example

1. Add a narrow `highlights.scm` pattern for a new declaration form.
2. Run `tree-sitter query` on a fixture that includes that declaration.
3. If captures are wrong, adjust pattern fields (not broad wildcards).
4. Re-run `...test_grammar` and `...doctor` to confirm no regressions.

Focus on faster grammar/query iteration and clearer test-quality outcomes.
