set shell := ["bash", "-euo", "pipefail", "-c"]

project_root := justfile_directory()

_default:
    @just --list

init:
    mkdir -p "{{project_root}}/grammars" "{{project_root}}/build" "{{project_root}}/logs"

add-grammar NAME URL:
    if [ -e "{{project_root}}/grammars/{{NAME}}" ]; then
        echo "Error: grammars/{{NAME}} already exists" >&2
        exit 1
    fi
    git -C "{{project_root}}" submodule add "{{URL}}" "grammars/{{NAME}}"

generate GRAMMAR:
    if [ ! -d "{{project_root}}/grammars/{{GRAMMAR}}" ]; then
        echo "Error: grammar directory not found: grammars/{{GRAMMAR}}" >&2
        exit 1
    fi
    tree-sitter generate --cwd "{{project_root}}/grammars/{{GRAMMAR}}"

build GRAMMAR: init
    grammar_dir="{{project_root}}/grammars/{{GRAMMAR}}"
    output_so="{{project_root}}/build/{{GRAMMAR}}.so"

    if [ ! -d "$grammar_dir" ]; then
        echo "Error: grammar directory not found: $grammar_dir" >&2
        exit 1
    fi

    start_ms=$(python -c 'import time; print(int(time.time() * 1000))')
    "{{project_root}}/scripts/build_grammar.sh" "$grammar_dir" "$output_so"
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

parse GRAMMAR SOURCE: init
    grammar_so="{{project_root}}/build/{{GRAMMAR}}.so"

    if [ ! -f "$grammar_so" ]; then
        echo "Error: built grammar not found: $grammar_so" >&2
        echo "Run 'just build {{GRAMMAR}}' first" >&2
        exit 1
    fi

    if [ ! -f "{{SOURCE}}" ]; then
        echo "Error: source file not found: {{SOURCE}}" >&2
        exit 1
    fi

    parse_result=$(mktemp)
    start_ms=$(python -c 'import time; print(int(time.time() * 1000))')
    tree-sitter parse --json --scope "source.{{GRAMMAR}}" "{{SOURCE}}" > "$parse_result"
    end_ms=$(python -c 'import time; print(int(time.time() * 1000))')
    parse_time_ms=$((end_ms - start_ms))

    "{{project_root}}/scripts/log_writer.py" parse \
        --grammar "{{GRAMMAR}}" \
        --source "{{SOURCE}}" \
        --parse-result "$parse_result" \
        --parse-time "$parse_time_ms" >> "{{project_root}}/logs/parses.jsonl"

    cat "$parse_result"
    rm -f "$parse_result"
