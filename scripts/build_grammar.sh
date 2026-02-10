#!/usr/bin/env bash
# scripts/build_grammar.sh
#
# Compile tree-sitter grammar to shared library.
# Usage: build_grammar.sh <grammar_dir> <output_so>

set -euo pipefail

SCRIPT_DIR=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)

"$SCRIPT_DIR/build/validate_inputs.sh" "$@"
GRAMMAR_DIR=$1
OUTPUT_SO=$2

LDFLAGS=$("$SCRIPT_DIR/build/detect_platform.sh")
SCANNER_INFO=$("$SCRIPT_DIR/build/detect_scanner.sh" "$GRAMMAR_DIR")
COMPILER=$(printf '%s\n' "$SCANNER_INFO" | cut -f1)
SCANNER=$(printf '%s\n' "$SCANNER_INFO" | cut -f2)

if [ -n "$SCANNER" ]; then
    "$SCRIPT_DIR/build/compile_shared_library.sh" "$COMPILER" "$LDFLAGS" "$GRAMMAR_DIR" "$OUTPUT_SO" "$SCANNER"
else
    "$SCRIPT_DIR/build/compile_shared_library.sh" "$COMPILER" "$LDFLAGS" "$GRAMMAR_DIR" "$OUTPUT_SO"
fi
