from __future__ import annotations

import argparse
import json
from pathlib import Path

from grammatic.contracts import BuildRequest, DoctorRequest, GenerateRequest, ParseRequest, TestGrammarRequest
from grammatic.workflows import handle_build, handle_doctor, handle_generate, handle_parse, handle_test_grammar


def _print_diagnostics(result: object) -> None:
    import sys

    diagnostics = getattr(result, "diagnostics", [])
    for diagnostic in diagnostics:
        if diagnostic.level == "error":
            print(diagnostic.message, file=sys.stderr)
        else:
            print(diagnostic.message)


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
