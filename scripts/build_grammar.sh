#!/usr/bin/env bash
# Thin compatibility wrapper around the canonical Python implementation.
# Usage: build_grammar.sh <grammar_dir> <output_so>

set -euo pipefail

SCRIPT_DIR=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)

exec "$SCRIPT_DIR/build_grammar.py" "$@"
