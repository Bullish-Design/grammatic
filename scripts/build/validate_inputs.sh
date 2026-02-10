#!/usr/bin/env bash
set -euo pipefail

if [ "$#" -ne 2 ]; then
    echo "Usage: $0 <grammar_dir> <output_so>" >&2
    exit 1
fi

grammar_dir=$1

if [ ! -d "$grammar_dir/src" ]; then
    echo "Error: $grammar_dir/src not found" >&2
    exit 1
fi

if [ ! -f "$grammar_dir/src/parser.c" ]; then
    echo "Error: $grammar_dir/src/parser.c not found" >&2
    echo "Run 'tree-sitter generate' in $grammar_dir first" >&2
    exit 1
fi
