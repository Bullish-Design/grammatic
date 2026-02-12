set shell := ["bash", "-euo", "pipefail", "-c"]

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
    #!/usr/bin/env bash
    if [ -e "{{project_root}}/grammars/{{NAME}}" ]; then
        echo "Error: grammars/{{NAME}} already exists" >&2
        exit 1
    fi
    git -C "{{project_root}}" submodule add "{{URL}}" "grammars/{{NAME}}"

update-grammars:
    git -C "{{project_root}}" submodule update --remote --merge

generate GRAMMAR:
    PYTHONPATH="{{project_root}}/src" python -m grammatic.cli --repo-root "{{project_root}}" generate "{{GRAMMAR}}"

build GRAMMAR: init
    PYTHONPATH="{{project_root}}/src" python -m grammatic.cli --repo-root "{{project_root}}" build "{{GRAMMAR}}"

rebuild GRAMMAR:
    just generate "{{GRAMMAR}}"
    just build "{{GRAMMAR}}"

parse GRAMMAR SOURCE: init
    PYTHONPATH="{{project_root}}/src" python -m grammatic.cli --repo-root "{{project_root}}" parse "{{GRAMMAR}}" "{{SOURCE}}"

test-grammar GRAMMAR: (build GRAMMAR)
    PYTHONPATH="{{project_root}}/src" python -m grammatic.cli --repo-root "{{project_root}}" test-grammar "{{GRAMMAR}}"

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
    PYTHONPATH="{{project_root}}/src" python -m grammatic.cli --repo-root "{{project_root}}" doctor "{{GRAMMAR}}"

query-builds N="10":
    PYTHONPATH="{{project_root}}/src" python -m grammatic.cli --repo-root "{{project_root}}" logs recent-builds --limit "{{N}}"

query-builds-for GRAMMAR:
    PYTHONPATH="{{project_root}}/src" python -m grammatic.cli --repo-root "{{project_root}}" logs recent-builds --grammar "{{GRAMMAR}}" --all

query-parses N="10":
    PYTHONPATH="{{project_root}}/src" python -m grammatic.cli --repo-root "{{project_root}}" logs recent-parses --limit "{{N}}"

query-failures:
    PYTHONPATH="{{project_root}}/src" python -m grammatic.cli --repo-root "{{project_root}}" logs recent-parses --failures-only --all

query-parses-for GRAMMAR:
    PYTHONPATH="{{project_root}}/src" python -m grammatic.cli --repo-root "{{project_root}}" logs recent-parses --grammar "{{GRAMMAR}}" --all

build-success-rate GRAMMAR:
    PYTHONPATH="{{project_root}}/src" python -m grammatic.cli --repo-root "{{project_root}}" logs build-success-rate "{{GRAMMAR}}"

avg-parse-time GRAMMAR:
    PYTHONPATH="{{project_root}}/src" python -m grammatic.cli --repo-root "{{project_root}}" logs avg-parse-time "{{GRAMMAR}}"

slowest-parses N="10":
    #!/usr/bin/env bash
    if [ ! -f "{{project_root}}/logs/parses.jsonl" ]; then
        echo '[]'
        exit 0
    fi
    jq -c '.' "{{project_root}}/logs/parses.jsonl" \
        | jq -s "sort_by(.duration_ms) | reverse | .[:{{N}}]"

grammar-versions GRAMMAR:
    #!/usr/bin/env bash
    if [ -f "{{project_root}}/logs/parses.jsonl" ]; then
        jq --arg grammar "{{GRAMMAR}}" -c 'select(.grammar == $grammar)' "{{project_root}}/logs/parses.jsonl" \
            | jq -r '.grammar_version' \
            | sort | uniq -c
    fi

export-logs OUTPUT:
    #!/usr/bin/env bash
    if [ ! -d "{{OUTPUT}}" ]; then
        echo "Error: output directory not found: {{OUTPUT}}" >&2
        exit 1
    fi

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
