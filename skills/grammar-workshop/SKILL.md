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
- diagnostics are clean or intentionally documented
- provenance/logging remains consistent

## Use This Interface

Prefer `just` commands with grammar names:

- `just generate <grammar>`
- `just build <grammar>`
- `just test-grammar <grammar>`
- `just doctor <grammar>`
- `just parse <grammar> <source>` (optional support check)

Avoid introducing path-heavy command UX in user-facing workflows.

## Canonical Loop

1. Ensure grammar exists or scaffold one (`just new-grammar <name>`)
2. Update grammar sources (`grammar.js`, scanner, corpus tests)
3. Generate parser artifacts
4. Build shared library
5. Run grammar corpus tests
6. Run doctor checks
7. Optionally parse a fixture for targeted debugging
8. Review logs if needed and iterate

## Path Conventions

- Grammar root: `grammars/<grammar>/`
- Build artifact: `build/<grammar>/<grammar>.so`
- Logs: `logs/builds.jsonl`, `logs/parses.jsonl`

## Implementation Rules

- Reuse tree-sitter CLI behavior instead of recreating it
- Keep scripts small and explicit
- Use robust preflight checks for required files/dirs
- Prefer actionable errors over silent fallthrough

## MVP Scope Guardrails

Do:
- improve workshop reliability
- improve testing ergonomics
- preserve grammar-name command contract

Avoid:
- over-abstracting orchestration
- introducing large framework layers
- making parse the center of the user story
