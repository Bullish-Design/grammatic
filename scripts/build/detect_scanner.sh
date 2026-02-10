#!/usr/bin/env bash
set -euo pipefail

if [ "$#" -ne 1 ]; then
    echo "Usage: $0 <grammar_dir>" >&2
    exit 1
fi

grammar_dir=$1

if [ -f "$grammar_dir/src/scanner.cc" ]; then
    echo "Using C++ scanner" >&2
    printf 'g++\t%s\n' "$grammar_dir/src/scanner.cc"
elif [ -f "$grammar_dir/src/scanner.c" ]; then
    echo "Using C scanner" >&2
    printf 'gcc\t%s\n' "$grammar_dir/src/scanner.c"
else
    echo "No scanner file found (parser only)" >&2
    printf 'gcc\t\n'
fi
