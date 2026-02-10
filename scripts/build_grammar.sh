#!/usr/bin/env bash
# scripts/build_grammar.sh
#
# Compile tree-sitter grammar to shared library.
# Usage: build_grammar.sh <grammar_dir> <output_so>

set -euo pipefail

if [ "$#" -ne 2 ]; then
    echo "Usage: $0 <grammar_dir> <output_so>" >&2
    exit 1
fi

GRAMMAR_DIR=$1
OUTPUT_SO=$2

if [ ! -d "$GRAMMAR_DIR/src" ]; then
    echo "Error: $GRAMMAR_DIR/src not found" >&2
    exit 1
fi

if [ ! -f "$GRAMMAR_DIR/src/parser.c" ]; then
    echo "Error: $GRAMMAR_DIR/src/parser.c not found" >&2
    echo "Run 'tree-sitter generate' in $GRAMMAR_DIR first" >&2
    exit 1
fi

case "$(uname -s)" in
    Linux*)
        LDFLAGS="-shared"
        ;;
    Darwin*)
        LDFLAGS="-dynamiclib"
        ;;
    *)
        echo "Unsupported platform: $(uname -s)" >&2
        exit 1
        ;;
esac

if [ -f "$GRAMMAR_DIR/src/scanner.cc" ]; then
    COMPILER="g++"
    SCANNER="$GRAMMAR_DIR/src/scanner.cc"
    echo "Using C++ scanner" >&2
elif [ -f "$GRAMMAR_DIR/src/scanner.c" ]; then
    COMPILER="gcc"
    SCANNER="$GRAMMAR_DIR/src/scanner.c"
    echo "Using C scanner" >&2
else
    COMPILER="gcc"
    SCANNER=""
    echo "No scanner file found (parser only)" >&2
fi

mkdir -p "$(dirname "$OUTPUT_SO")"

echo "Compiling: $GRAMMAR_DIR -> $OUTPUT_SO" >&2
if [ -n "$SCANNER" ]; then
    "$COMPILER" "$LDFLAGS" -fPIC -O2 \
        -I"$GRAMMAR_DIR/src" \
        "$GRAMMAR_DIR/src/parser.c" \
        "$SCANNER" \
        -o "$OUTPUT_SO"
else
    "$COMPILER" "$LDFLAGS" -fPIC -O2 \
        -I"$GRAMMAR_DIR/src" \
        "$GRAMMAR_DIR/src/parser.c" \
        -o "$OUTPUT_SO"
fi

if [ ! -f "$OUTPUT_SO" ]; then
    echo "Error: Build failed - $OUTPUT_SO not created" >&2
    exit 1
fi

echo "Build successful: $OUTPUT_SO" >&2
