#!/usr/bin/env -S uv run --no-project

from __future__ import annotations

import platform
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))
from grammatic.errors import ArtifactMissingError, SubprocessExecutionError, ValidationError


def print_usage() -> None:
    script_name = Path(sys.argv[0]).name
    print(f"Usage: {script_name} <grammar_dir> <output_so>", file=sys.stderr)


def validate_inputs(grammar_dir: Path) -> None:
    src_dir = grammar_dir / "src"
    parser_c = src_dir / "parser.c"

    if not src_dir.is_dir():
        raise ValidationError(f"Error: {src_dir} not found")

    if not parser_c.is_file():
        raise ArtifactMissingError(f"Error: {parser_c} not found\nRun 'tree-sitter generate' in {grammar_dir} first")


def detect_platform_flag() -> str:
    system = platform.system()
    if system == "Linux":
        return "-shared"
    if system == "Darwin":
        return "-dynamiclib"
    raise ValidationError(f"Unsupported platform: {system}")


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
    result = subprocess.run(cmd, check=False, capture_output=True, text=True)
    if result.returncode != 0:
        raise SubprocessExecutionError(
            command=cmd,
            returncode=result.returncode,
            stderr=result.stderr.strip(),
            stdout=result.stdout.strip(),
            message="Grammar compilation failed",
        )

    if not output_so.is_file():
        raise ArtifactMissingError(f"Error: Build failed - {output_so} not created")

    print(f"Build successful: {output_so}", file=sys.stderr)


def map_error(exc: Exception) -> int:
    if isinstance(exc, (ValidationError, ArtifactMissingError)):
        print(exc, file=sys.stderr)
        return 1
    if isinstance(exc, SubprocessExecutionError):
        print(exc, file=sys.stderr)
        if exc.stderr:
            print(exc.stderr, file=sys.stderr)
        return 1
    print(exc, file=sys.stderr)
    return 1


def main() -> int:
    if len(sys.argv) != 3:
        print_usage()
        return 1

    grammar_dir = Path(sys.argv[1])
    output_so = Path(sys.argv[2])

    try:
        validate_inputs(grammar_dir)
        ldflag = detect_platform_flag()
        compiler, scanner = detect_scanner(grammar_dir)
        compile_shared_library(compiler, ldflag, grammar_dir, output_so, scanner)
    except Exception as exc:
        return map_error(exc)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
