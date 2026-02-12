---
name: query-workshop
description: Workflow for agents to create, modify, and evaluate tree-sitter .scm query files for grammars in Grammatic.
---

# Query Workshop Skill

Use this skill when the task is to add, update, validate, or review tree-sitter query files (`.scm`) for a grammar in this repository.

## Intent

Optimize for high-signal query behavior that improves grammar usability (highlighting, locals, injections, tags) while preserving the core grammar workshop loop.

Primary outcomes:
- query files are clear and maintainable
- captures align with real syntax nodes from the target grammar
- query behavior is validated against representative fixtures
- changes are easy to iterate with existing Grammatic commands and tools

## Scope + Relationship to Grammar Workflow

The grammar workshop loop remains primary. Query work should be anchored to the grammar-name flow:

1. Ensure grammar compiles and tests cleanly (`just generate`, `just build`, `just test-grammar`, `just doctor`)
2. Implement or modify query files
3. Validate queries on realistic source fixtures
4. Iterate on captures/patterns until behavior is stable

Use `grammar-workshop` skill for parser/corpus changes; use this skill for `.scm` semantics.

## Canonical Query File Locations

Within `grammars/<grammar>/`, prefer tree-sitter conventions:

- `queries/highlights.scm`
- `queries/injections.scm`
- `queries/locals.scm`
- `queries/tags.scm`

If a grammar already uses an alternate layout, preserve local conventions unless explicitly migrating.

## Query Authoring Guidelines

1. Work from concrete node names
   - Inspect `grammar.js` and corpus expectations first
   - Match actual node/type names exactly

2. Keep patterns specific before generalizing
   - Start with narrow patterns that are easy to verify
   - Add alternations/abstractions only when repeated structure is proven

3. Prefer readable captures
   - Use capture names with clear intent (`@function`, `@type`, `@variable`, etc.)
   - Group related patterns and add short comments for non-obvious logic

4. Avoid fragile overmatching
   - Use field constraints and structural context when possible
   - Be careful with wildcard-heavy patterns that may degrade precision

5. Keep compatibility in mind
   - Use capture names expected by downstream tooling for the query type
   - Do not rename commonly consumed captures without documenting impact

## Evaluation Workflow

For the target grammar `<grammar>`:

1. Validate grammar baseline
   - `just generate <grammar>`
   - `just build <grammar>`
   - `just test-grammar <grammar>`
   - `just doctor <grammar>`

2. Run focused parse checks on sample inputs
   - `just parse <grammar> <source>`
   - choose sources that exercise newly targeted constructs

3. Evaluate query behavior with tree-sitter query tooling
   - run `tree-sitter query` against the grammar's `.scm` files and source fixtures
   - compare capture output against expected semantic intent

4. Iterate and re-check
   - adjust patterns/captures
   - re-run query checks and grammar tests

## Repository-Specific Practices

- Keep orchestration thin: rely on `just` + `tree-sitter` instead of custom frameworks
- Prefer grammar-name-first workflow when invoking project commands
- Keep changes local to a grammar unless intentionally introducing shared conventions
- If query edits depend on grammar node changes, update corpus tests first-class

## Review Checklist (for PRs and agent handoff)

- Grammar builds and corpus tests still pass
- Query files are placed in expected grammar paths
- Added/changed captures are justified by real syntax examples
- No obvious broad pattern that captures unrelated constructs
- Complex patterns include brief comments
- Any intentionally breaking capture-name changes are documented

## Common Pitfalls

- Using node names not emitted by the current parser
- Relying on anonymous tokens where named nodes are available
- Adding broad fallback patterns too early
- Editing query captures without validating against representative fixtures
- Mixing grammar refactors and query refactors in one large, unreviewable change
