from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from grammatic.contracts import BuildRequest, DoctorRequest, GenerateRequest, ParseRequest, TestGrammarRequest
from grammatic.errors import (
    ArtifactMissingError,
    GrammaticError,
    LogWriteError,
    SubprocessExecutionError,
    ToolMissingError,
    ValidationError,
)
from grammatic.workflows import handle_build, handle_doctor, handle_generate, handle_parse, handle_test_grammar


EXIT_CODES: dict[type[GrammaticError], int] = {
    ValidationError: 2,
    ToolMissingError: 3,
    SubprocessExecutionError: 4,
    ArtifactMissingError: 5,
    LogWriteError: 6,
}


def _print_diagnostics(result: object) -> None:
    diagnostics = getattr(result, "diagnostics", [])
    for diagnostic in diagnostics:
        if diagnostic.level == "error":
            print(diagnostic.message, file=sys.stderr)
        else:
            print(diagnostic.message)


def _map_error(exc: Exception) -> tuple[int, str]:
    if isinstance(exc, GrammaticError):
        code = EXIT_CODES.get(type(exc), 1)
        return code, f"[grammatic:{type(exc).__name__}] {exc}"
    return 1, f"[grammatic:UnhandledError] {exc}"


def main() -> int:
    parser = argparse.ArgumentParser(prog="grammatic", description="Grammar workshop workflow CLI")
    parser.add_argument("--repo-root", default=Path.cwd(), type=Path)
    sub = parser.add_subparsers(dest="command", required=True)

    for name in ("generate", "build", "test-grammar", "doctor"):
        cmd = sub.add_parser(name)
        cmd.add_argument("grammar")

    parse_cmd = sub.add_parser("parse")
    parse_cmd.add_argument("grammar")
    parse_cmd.add_argument("source", type=Path)

    args = parser.parse_args()

    try:
        if args.command == "generate":
            result = handle_generate(GenerateRequest(grammar=args.grammar, repo_root=args.repo_root))
        elif args.command == "build":
            result = handle_build(BuildRequest(grammar=args.grammar, repo_root=args.repo_root))
        elif args.command == "parse":
            result = handle_parse(ParseRequest(grammar=args.grammar, repo_root=args.repo_root, source=args.source))
        elif args.command == "test-grammar":
            result = handle_test_grammar(TestGrammarRequest(grammar=args.grammar, repo_root=args.repo_root))
        else:
            result = handle_doctor(DoctorRequest(grammar=args.grammar, repo_root=args.repo_root))
    except Exception as exc:  # central CLI mapper
        code, message = _map_error(exc)
        print(message, file=sys.stderr)
        if isinstance(exc, SubprocessExecutionError):
            if exc.stderr:
                print(exc.stderr, file=sys.stderr)
            elif exc.stdout:
                print(exc.stdout, file=sys.stderr)
        return code

    _print_diagnostics(result)

    if args.command == "parse" and getattr(result, "status", "error") == "ok":
        print(json.dumps(result.parse_output, indent=2))

    if args.command == "doctor" and getattr(result, "status", "error") == "error":
        print(f"Issues found for grammar '{args.grammar}':")
        for finding in result.findings:
            print(f"  ✗ {finding}")

    return 0 if getattr(result, "status", "error") == "ok" else 1


if __name__ == "__main__":
    raise SystemExit(main())
