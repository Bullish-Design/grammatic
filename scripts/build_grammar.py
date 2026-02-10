#!/usr/bin/env -S uv run --no-project

from __future__ import annotations

import platform
import subprocess
import sys
from pathlib import Path


def print_usage() -> None:
    script_name = Path(sys.argv[0]).name
    print(f"Usage: {script_name} <grammar_dir> <output_so>", file=sys.stderr)


def validate_inputs(grammar_dir: Path) -> None:
    src_dir = grammar_dir / "src"
    parser_c = src_dir / "parser.c"

    if not src_dir.is_dir():
        print(f"Error: {src_dir} not found", file=sys.stderr)
        raise SystemExit(1)

    if not parser_c.is_file():
        print(f"Error: {parser_c} not found", file=sys.stderr)
        print(f"Run 'tree-sitter generate' in {grammar_dir} first", file=sys.stderr)
        raise SystemExit(1)


def detect_platform_flag() -> str:
    system = platform.system()
    if system == "Linux":
        return "-shared"
    if system == "Darwin":
        return "-dynamiclib"

    print(f"Unsupported platform: {system}", file=sys.stderr)
    raise SystemExit(1)


def detect_scanner(grammar_dir: Path) -> tuple[str, Path | None]:
    scanner_cc = grammar_dir / "src" / "scanner.cc"
    scanner_c = grammar_dir / "src" / "scanner.c"

    if scanner_cc.is_file():
        print("Using C++ scanner", file=sys.stderr)
        return "g++", scanner_cc

    if scanner_c.is_file():
        print("Using C scanner", file=sys.stderr)
        return "gcc", scanner_c

    print("No scanner file found (parser only)", file=sys.stderr)
    return "gcc", None


def compile_shared_library(
    compiler: str,
    ldflag: str,
    grammar_dir: Path,
    output_so: Path,
    scanner: Path | None,
) -> None:
    output_so.parent.mkdir(parents=True, exist_ok=True)

    cmd = [
        compiler,
        ldflag,
        "-fPIC",
        "-O2",
        f"-I{grammar_dir / 'src'}",
        str(grammar_dir / "src" / "parser.c"),
    ]
    if scanner is not None:
        cmd.append(str(scanner))
    cmd.extend(["-o", str(output_so)])

    print(f"Compiling: {grammar_dir} -> {output_so}", file=sys.stderr)
    subprocess.run(cmd, check=True)

    if not output_so.is_file():
        print(f"Error: Build failed - {output_so} not created", file=sys.stderr)
        raise SystemExit(1)

    print(f"Build successful: {output_so}", file=sys.stderr)


def main() -> None:
    if len(sys.argv) != 3:
        print_usage()
        raise SystemExit(1)

    grammar_dir = Path(sys.argv[1])
    output_so = Path(sys.argv[2])

    validate_inputs(grammar_dir)
    ldflag = detect_platform_flag()
    compiler, scanner = detect_scanner(grammar_dir)
    compile_shared_library(compiler, ldflag, grammar_dir, output_so, scanner)


if __name__ == "__main__":
    main()
