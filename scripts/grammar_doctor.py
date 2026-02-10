#!/usr/bin/env python3
from __future__ import annotations

import sys
from pathlib import Path


def check_grammar(project_root: Path, grammar: str) -> list[str]:
    """Check grammar and return a list of issues."""
    issues: list[str] = []
    grammar_dir = project_root / "grammars" / grammar

    if not grammar_dir.exists():
        issues.append(f"Grammar directory not found: {grammar_dir}")
        return issues

    grammar_js = grammar_dir / "grammar.js"
    if not grammar_js.exists():
        issues.append("Missing grammar.js")

    if not (grammar_dir / "src" / "parser.c").exists():
        issues.append(f"Parser not generated. Run: just generate {grammar}")

    built_nested = project_root / "build" / grammar / f"{grammar}.so"
    built_flat = project_root / "build" / f"{grammar}.so"
    if not built_nested.exists() and not built_flat.exists():
        issues.append(f"Grammar not built. Run: just build {grammar}")

    corpus_dir = grammar_dir / "test" / "corpus"
    if not corpus_dir.exists():
        issues.append("No corpus tests directory")
    elif not list(corpus_dir.glob("*.txt")):
        issues.append("No corpus test files")

    has_c_scanner = (grammar_dir / "src" / "scanner.c").exists()
    has_cpp_scanner = (grammar_dir / "src" / "scanner.cc").exists()
    if not has_c_scanner and not has_cpp_scanner and grammar_js.exists():
        content = grammar_js.read_text(encoding="utf-8")
        if "externals:" in content:
            issues.append("Grammar uses externals but no scanner.c/scanner.cc found")

    return issues


def main() -> int:
    if len(sys.argv) != 2:
        print("Usage: grammar_doctor.py GRAMMAR", file=sys.stderr)
        return 1

    project_root = Path(__file__).resolve().parents[1]
    grammar = sys.argv[1]
    issues = check_grammar(project_root, grammar)

    if not issues:
        print(f"✓ Grammar '{grammar}' looks good!")
        return 0

    print(f"Issues found for grammar '{grammar}':")
    for issue in issues:
        print(f"  ✗ {issue}")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
