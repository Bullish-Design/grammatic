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
