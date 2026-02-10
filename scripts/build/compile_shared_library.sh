#!/usr/bin/env bash
set -euo pipefail

if [ "$#" -lt 4 ] || [ "$#" -gt 5 ]; then
    echo "Usage: $0 <compiler> <ldflags> <grammar_dir> <output_so> [scanner]" >&2
    exit 1
fi

compiler=$1
ldflags=$2
grammar_dir=$3
output_so=$4
scanner=${5:-}

mkdir -p "$(dirname "$output_so")"

echo "Compiling: $grammar_dir -> $output_so" >&2
if [ -n "$scanner" ]; then
    "$compiler" "$ldflags" -fPIC -O2 \
        -I"$grammar_dir/src" \
        "$grammar_dir/src/parser.c" \
        "$scanner" \
        -o "$output_so"
else
    "$compiler" "$ldflags" -fPIC -O2 \
        -I"$grammar_dir/src" \
        "$grammar_dir/src/parser.c" \
        -o "$output_so"
fi

if [ ! -f "$output_so" ]; then
    echo "Error: Build failed - $output_so not created" >&2
    exit 1
fi

echo "Build successful: $output_so" >&2
