# Grammatic

Grammatic is a devenv-managed toolkit for building and validating tree-sitter grammars with `just` recipes that wrap tree-sitter cli functionality. It focuses on reproducible grammar workflows, shell-first automation, and append-only provenance for build and parse runs.

## Quick Start

```bash
devenv shell
just init
just add-grammar python https://github.com/tree-sitter/tree-sitter-python
just generate python
just build python
just parse python tests/fixtures/example.py
```

## Documentation

- Development guide: [`AGENTS.md`](./AGENTS.md#grammatic-development-guide)
- Architecture summary: [`AGENTS.md`](./AGENTS.md#architecture-at-a-glance)

## Python Version Policy

- Canonical development runtime: **Python 3.13 via `devenv shell`**.

### `uv run` vs `devenv shell`

- Assume all work is being done inside the `devenv shell` with the full toolchain (`tree-sitter`, compilers, `jq`, `just`, `uv`) available, since devenv provides the pinned system dependencies and canonical Python runtime.
- Ensure all `just` scripts are written for this scenario, and are always run from the repo root

## Build Implementation

Grammatic uses a single canonical build entrypoint: `scripts/build_grammar.py`. 
