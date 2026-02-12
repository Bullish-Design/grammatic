# Grammatic

Grammatic is a devenv-managed toolkit for building and validating tree-sitter grammars with `just` recipes and JSONL event logs. It focuses on reproducible grammar workflows, shell-first automation, and append-only provenance for build and parse runs.

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

- Supported project range: **Python 3.12 to 3.13** (`>=3.12,<3.14`).
- Canonical development runtime: **Python 3.13 via `devenv shell`**.

### `uv run` vs `devenv shell`

- Use `uv run <command>` for Python-only tasks (for example, running scripts or tests) once your environment is bootstrapped.
- Use `devenv shell` when you need the full toolchain (`tree-sitter`, compilers, `jq`, `just`) or when setting up a fresh machine/session, since it provides the pinned system dependencies and canonical Python runtime.

## Build Implementation

Grammatic uses a single canonical build entrypoint: `scripts/build_grammar.py`. The `scripts/build_grammar.sh` file is only a thin compatibility wrapper that delegates to the Python script.
