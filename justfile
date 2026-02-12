set shell := ["bash", "-euo", "pipefail", "-c"]

import "scripts/just/path_checks.just"

project_root := justfile_directory()

_default:
    @just --list

help:
    @just --list

init:
    mkdir -p "{{project_root}}/grammars" "{{project_root}}/build" "{{project_root}}/logs" "{{project_root}}/schemas" "{{project_root}}/tests/fixtures"
    git -C "{{project_root}}" submodule init
    echo "Grammatic initialized"
    echo "Add grammars with: just add-grammar NAME URL"

add-grammar NAME URL:
    just check-missing "{{project_root}}/grammars/{{NAME}}" "Error: grammars/{{NAME}} already exists"
    git -C "{{project_root}}" submodule add "{{URL}}" "grammars/{{NAME}}"

update-grammars:
    git -C "{{project_root}}" submodule update --remote --merge

generate GRAMMAR:
    just check-dir "{{project_root}}/grammars/{{GRAMMAR}}" "Error: grammar directory not found: grammars/{{GRAMMAR}}"
    cd "{{project_root}}/grammars/{{GRAMMAR}}" && tree-sitter generate

build GRAMMAR: init
    #!/usr/bin/env bash
    grammar_dir="{{project_root}}/grammars/{{GRAMMAR}}"
    output_so="{{project_root}}/build/{{GRAMMAR}}/{{GRAMMAR}}.so"

    just check-dir "$grammar_dir" "Error: grammar directory not found: $grammar_dir"

    start_ms=$(python -c 'import time; print(int(time.time() * 1000))')
    "{{project_root}}/scripts/build_grammar.py" "$grammar_dir" "$output_so"
    end_ms=$(python -c 'import time; print(int(time.time() * 1000))')
    build_time_ms=$((end_ms - start_ms))

    commit=$(git -C "$grammar_dir" rev-parse HEAD)
    repo_url=$(git -C "$grammar_dir" config --get remote.origin.url)
    tree_sitter_version=$(tree-sitter --version | awk '{print $2}')

    "{{project_root}}/scripts/log_writer.py" build \
        --grammar "{{GRAMMAR}}" \
        --commit "$commit" \
        --repo-url "$repo_url" \
        --so-path "$output_so" \
        --build-time "$build_time_ms" \
        --tree-sitter-version "$tree_sitter_version" >> "{{project_root}}/logs/builds.jsonl"

rebuild GRAMMAR:
    just generate "{{GRAMMAR}}"
    just build "{{GRAMMAR}}"

parse GRAMMAR SOURCE: init
    #!/usr/bin/env bash
    set -euo pipefail

    grammar_so="{{project_root}}/build/{{GRAMMAR}}/{{GRAMMAR}}.so"

    just check-file "$grammar_so" "Error: built grammar not found: $grammar_so. Run 'just build {{GRAMMAR}}' first"
    just check-file "{{SOURCE}}" "Error: source file not found: {{SOURCE}}"

    parse_result=$(mktemp)
    trap 'rm -f "$parse_result"' EXIT

    start_ms=$(python -c 'import time; print(int(time.time() * 1000))')
    tree-sitter parse "{{SOURCE}}" --language "$grammar_so" --json > "$parse_result"
    [ -s "$parse_result" ] || {
        echo "Error: parse output is empty" >&2
        exit 1
    }

    if ! jq -e '.' "$parse_result" > /dev/null; then
        echo "Error: parse output is not valid JSON" >&2
        exit 1
    fi

    end_ms=$(python -c 'import time; print(int(time.time() * 1000))')
    parse_time_ms=$((end_ms - start_ms))

    "{{project_root}}/scripts/log_writer.py" parse \
        --grammar "{{GRAMMAR}}" \
        --source "{{SOURCE}}" \
        --parse-result "$parse_result" \
        --parse-time "$parse_time_ms" >> "{{project_root}}/logs/parses.jsonl"

    jq '.' "$parse_result"
    echo ""
    echo "Parse logged to parses.jsonl"

test-grammar GRAMMAR: (build GRAMMAR)
    #!/usr/bin/env bash
    grammar_dir="{{project_root}}/grammars/{{GRAMMAR}}"
    grammar_so="{{project_root}}/build/{{GRAMMAR}}/{{GRAMMAR}}.so"
    corpus_dir="{{project_root}}/grammars/{{GRAMMAR}}/test/corpus"

    just check-dir "$grammar_dir" "Error: grammar directory not found: $grammar_dir"
    just check-dir "$corpus_dir" "Error: No corpus tests found for {{GRAMMAR}}"
    just check-file "$grammar_so" "Error: built grammar not found: $grammar_so. Run 'just build {{GRAMMAR}}' first"

    if ! tree-sitter test --help | rg -q -- '--language'; then
        echo "Error: current tree-sitter CLI does not support 'tree-sitter test --language'. Upgrade tree-sitter to run corpus tests against $grammar_so" >&2
        exit 1
    fi

    cd "$grammar_dir" && tree-sitter test --language "$grammar_so"

test GRAMMAR:
    just test-grammar "{{GRAMMAR}}"
    just parse "{{GRAMMAR}}" "{{project_root}}/tests/fixtures/sample_{{GRAMMAR}}.txt"

# Watch grammar for changes and rebuild
watch GRAMMAR:
    #!/usr/bin/env bash
    if [ ! -d "{{project_root}}/grammars/{{GRAMMAR}}" ]; then
        echo "Error: Grammar {{GRAMMAR}} not found" >&2
        exit 1
    fi

    echo "Watching {{project_root}}/grammars/{{GRAMMAR}}/grammar.js for changes..."
    watchexec --watch "{{project_root}}/grammars/{{GRAMMAR}}/grammar.js" \
        --clear \
        --restart \
        -- just rebuild {{GRAMMAR}}

# Create new custom grammar from template
new-grammar NAME:
    #!/usr/bin/env bash
    if [ -d "{{project_root}}/grammars/{{NAME}}" ]; then
        echo "Error: Grammar {{NAME}} already exists" >&2
        exit 1
    fi

    "{{project_root}}/scripts/new_grammar.sh" "{{project_root}}" "{{NAME}}"


# List all available grammars
list-grammars:
    #!/usr/bin/env bash
    if [ ! -d "{{project_root}}/grammars" ]; then
        echo "No grammars directory found. Run: just init" >&2
        exit 1
    fi

    echo "Available grammars:"
    shopt -s nullglob
    dirs=("{{project_root}}"/grammars/*/)
    if [ "${#dirs[@]}" -eq 0 ]; then
        echo "  (none found)"
        exit 0
    fi

    for dir in "${dirs[@]}"; do
        grammar=$(basename "$dir")
        if [ -f "{{project_root}}/build/$grammar/$grammar.so" ]; then
            echo "  ✓ $grammar (built)"
        else
            echo "  ✗ $grammar (not built)"
        fi
    done

# Show grammar info
info GRAMMAR:
    #!/usr/bin/env bash
    if [ ! -d "{{project_root}}/grammars/{{GRAMMAR}}" ]; then
        echo "Error: Grammar {{GRAMMAR}} not found" >&2
        exit 1
    fi

    echo "Grammar: {{GRAMMAR}}"
    echo "Path: grammars/{{GRAMMAR}}"

    if [ -f "{{project_root}}/grammars/{{GRAMMAR}}/grammar.js" ]; then
        echo "Grammar file: ✓"
    else
        echo "Grammar file: ✗"
    fi

    if [ -f "{{project_root}}/grammars/{{GRAMMAR}}/src/parser.c" ]; then
        echo "Parser generated: ✓"
    else
        echo "Parser generated: ✗"
    fi

    if [ -f "{{project_root}}/build/{{GRAMMAR}}/{{GRAMMAR}}.so" ]; then
        echo "Built: ✓ (build/{{GRAMMAR}}/{{GRAMMAR}}.so)"
    else
        echo "Built: ✗"
    fi

    if [ -d "{{project_root}}/grammars/{{GRAMMAR}}/test/corpus" ]; then
        test_count=$(find "{{project_root}}/grammars/{{GRAMMAR}}/test/corpus" -name "*.txt" | wc -l)
        echo "Corpus tests: $test_count file(s)"
    else
        echo "Corpus tests: none"
    fi

    if git -C "{{project_root}}/grammars/{{GRAMMAR}}" rev-parse --git-dir > /dev/null 2>&1; then
        commit=$(git -C "{{project_root}}/grammars/{{GRAMMAR}}" rev-parse --short HEAD)
        echo "Git commit: $commit"

        if git -C "{{project_root}}/grammars/{{GRAMMAR}}" remote get-url origin > /dev/null 2>&1; then
            url=$(git -C "{{project_root}}/grammars/{{GRAMMAR}}" remote get-url origin)
            echo "Remote: $url"
        fi
    fi

# Check grammar for common issues
doctor GRAMMAR:
    python "{{project_root}}/scripts/grammar_doctor.py" "{{GRAMMAR}}"

query-builds N="10":
    #!/usr/bin/env bash
    if [ -f "{{project_root}}/logs/builds.jsonl" ]; then
        jq -c '.' "{{project_root}}/logs/builds.jsonl" | tail -n "{{N}}"
    fi

query-builds-for GRAMMAR:
    #!/usr/bin/env bash
    grammar={{ quote(GRAMMAR) }}
    if [ -f "{{project_root}}/logs/builds.jsonl" ]; then
        jq --arg grammar "$grammar" -c 'select(.grammar == $grammar)' "{{project_root}}/logs/builds.jsonl"
    fi

query-parses N="10":
    #!/usr/bin/env bash
    if [ -f "{{project_root}}/logs/parses.jsonl" ]; then
        jq -c '.' "{{project_root}}/logs/parses.jsonl" | tail -n "{{N}}"
    fi

query-failures:
    #!/usr/bin/env bash
    if [ -f "{{project_root}}/logs/parses.jsonl" ]; then
        jq -c 'select(.has_errors == true)' "{{project_root}}/logs/parses.jsonl"
    fi

query-parses-for GRAMMAR:
    #!/usr/bin/env bash
    grammar={{ quote(GRAMMAR) }}
    if [ -f "{{project_root}}/logs/parses.jsonl" ]; then
        jq --arg grammar "$grammar" -c 'select(.grammar == $grammar)' "{{project_root}}/logs/parses.jsonl"
    fi

build-success-rate GRAMMAR:
    #!/usr/bin/env bash
    grammar={{ quote(GRAMMAR) }}
    if [ ! -f "{{project_root}}/logs/builds.jsonl" ]; then
        echo '[]'
        exit 0
    fi
    jq --arg grammar "$grammar" -c 'select(.grammar == $grammar)' "{{project_root}}/logs/builds.jsonl" \
        | jq -s 'group_by(.build_success) | map({success: .[0].build_success, count: length})'

avg-parse-time GRAMMAR:
    #!/usr/bin/env bash
    if [ ! -f "{{project_root}}/logs/parses.jsonl" ]; then
        echo "0"
        exit 0
    fi
    jq --arg grammar "{{GRAMMAR}}" -c 'select(.grammar == $grammar)' "{{project_root}}/logs/parses.jsonl" \
        | jq -s 'if length == 0 then 0 else (map(.parse_time_ms) | add / length) end'

slowest-parses N="10":
    #!/usr/bin/env bash
    if [ ! -f "{{project_root}}/logs/parses.jsonl" ]; then
        echo '[]'
        exit 0
    fi
    jq -c '.' "{{project_root}}/logs/parses.jsonl" \
        | jq -s "sort_by(.parse_time_ms) | reverse | .[:{{N}}]"

grammar-versions GRAMMAR:
    #!/usr/bin/env bash
    if [ -f "{{project_root}}/logs/parses.jsonl" ]; then
        jq --arg grammar "{{GRAMMAR}}" -c 'select(.grammar == $grammar)' "{{project_root}}/logs/parses.jsonl" \
            | jq -r '.grammar_version' \
            | sort | uniq -c
    fi

export-logs OUTPUT:
    #!/usr/bin/env bash
    just check-dir "{{OUTPUT}}" "Error: output directory not found: {{OUTPUT}}"

    shopt -s nullglob
    log_files=("{{project_root}}"/logs/*.jsonl)
    if [ "${#log_files[@]}" -eq 0 ]; then
        echo "Error: no log files found in {{project_root}}/logs" >&2
        exit 1
    fi

    timestamp=$(date +%Y%m%d-%H%M%S)
    archive="{{OUTPUT}}/grammatic-logs-${timestamp}.tar.gz"
    tar czf "$archive" -C "{{project_root}}" logs
    echo "Logs exported to $archive"

validate-logs:
    #!/usr/bin/env bash
    invalid=0

    echo "Validating builds.jsonl..."
    if [ -f "{{project_root}}/logs/builds.jsonl" ]; then
        if jq -e '.' "{{project_root}}/logs/builds.jsonl" > /dev/null; then
            echo "builds.jsonl is valid"
        else
            echo "builds.jsonl has invalid JSON" >&2
            invalid=1
        fi
    else
        echo "builds.jsonl not found, skipping"
    fi

    echo "Validating parses.jsonl..."
    if [ -f "{{project_root}}/logs/parses.jsonl" ]; then
        if jq -e '.' "{{project_root}}/logs/parses.jsonl" > /dev/null; then
            echo "parses.jsonl is valid"
        else
            echo "parses.jsonl has invalid JSON" >&2
            invalid=1
        fi
    else
        echo "parses.jsonl not found, skipping"
    fi

    if [ "$invalid" -ne 0 ]; then
        echo "Log validation failed" >&2
        exit 1
    fi

    echo "Log validation complete"

clean:
    find "{{project_root}}/build" -type f -name '*.so' -delete

clean-all: clean
    find "{{project_root}}/logs" -type f -name '*.jsonl' -delete
