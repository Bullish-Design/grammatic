set shell := ["bash", "-euo", "pipefail", "-c"]

import "scripts/just/path_checks.just"

project_root := justfile_directory()

_default:
    @just --list

init:
    mkdir -p "{{project_root}}/grammars" "{{project_root}}/build" "{{project_root}}/logs"

add-grammar NAME URL:
    just check-missing "{{project_root}}/grammars/{{NAME}}" "Error: grammars/{{NAME}} already exists"
    git -C "{{project_root}}" submodule add "{{URL}}" "grammars/{{NAME}}"

generate GRAMMAR:
    just check-dir "{{project_root}}/grammars/{{GRAMMAR}}" "Error: grammar directory not found: grammars/{{GRAMMAR}}"
    tree-sitter generate --cwd "{{project_root}}/grammars/{{GRAMMAR}}"

build GRAMMAR: init
    grammar_dir="{{project_root}}/grammars/{{GRAMMAR}}"
    output_so="{{project_root}}/build/{{GRAMMAR}}.so"

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

parse GRAMMAR SOURCE: init
    grammar_so="{{project_root}}/build/{{GRAMMAR}}.so"

    just check-file "$grammar_so" "Error: built grammar not found: $grammar_so. Run 'just build {{GRAMMAR}}' first"
    just check-file "{{SOURCE}}" "Error: source file not found: {{SOURCE}}"

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
