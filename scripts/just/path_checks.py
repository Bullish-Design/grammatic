#!/usr/bin/env -S uv run
# /// script
# ///

from __future__ import annotations

import sys
from pathlib import Path


def usage() -> None:
    print(f"Usage: {Path(sys.argv[0]).name} <missing|dir|file> <path> <error-message>", file=sys.stderr)
    raise SystemExit(2)


def main() -> None:
    if len(sys.argv) != 4:
        usage()

    check_type, raw_path, error_message = sys.argv[1:]
    path = Path(raw_path)

    if check_type == "missing":
        if path.exists():
            print(error_message, file=sys.stderr)
            raise SystemExit(1)
        return

    if check_type == "dir":
        if not path.is_dir():
            print(error_message, file=sys.stderr)
            raise SystemExit(1)
        return

    if check_type == "file":
        if not path.is_file():
            print(error_message, file=sys.stderr)
            raise SystemExit(1)
        return

    usage()


if __name__ == "__main__":
    main()
