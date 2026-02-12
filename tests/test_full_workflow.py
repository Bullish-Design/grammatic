from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[1]


def require_toolchain() -> None:
    missing = [
        tool
        for tool in ("git", "just", "tree-sitter", "uv", "jq", "gcc", "python")
        if shutil.which(tool) is None
    ]
    if missing:
        pytest.skip(f"Required tool(s) unavailable in PATH: {', '.join(missing)}")


@pytest.fixture
def test_repo(tmp_path: Path) -> Path:
    require_toolchain()

    repo = tmp_path / "test_repo"
    repo.mkdir()

    subprocess.run(["git", "init"], check=True, capture_output=True, cwd=repo)
    subprocess.run(["git", "config", "user.name", "Test"], check=True, capture_output=True, cwd=repo)
    subprocess.run(["git", "config", "user.email", "test@test.com"], check=True, capture_output=True, cwd=repo)

    (repo / "scripts" / "just").mkdir(parents=True)
    (repo / "src" / "grammatic").mkdir(parents=True)
    (repo / "tests" / "fixtures").mkdir(parents=True)

    shutil.copy(PROJECT_ROOT / "justfile", repo / "justfile")
    shutil.copy(PROJECT_ROOT / "scripts" / "build_grammar.py", repo / "scripts" / "build_grammar.py")
    shutil.copy(PROJECT_ROOT / "scripts" / "log_writer.py", repo / "scripts" / "log_writer.py")
    shutil.copy(PROJECT_ROOT / "scripts" / "query_logs.py", repo / "scripts" / "query_logs.py")
    shutil.copy(PROJECT_ROOT / "scripts" / "grammar_doctor.py", repo / "scripts" / "grammar_doctor.py")
    shutil.copy(PROJECT_ROOT / "scripts" / "new_grammar.sh", repo / "scripts" / "new_grammar.sh")
    shutil.copy(PROJECT_ROOT / "scripts" / "just" / "path_checks.just", repo / "scripts" / "just" / "path_checks.just")
    shutil.copy(PROJECT_ROOT / "scripts" / "just" / "path_checks.py", repo / "scripts" / "just" / "path_checks.py")
    shutil.copy(PROJECT_ROOT / "src" / "grammatic" / "models.py", repo / "src" / "grammatic" / "models.py")
    shutil.copy(PROJECT_ROOT / "src" / "grammatic" / "__init__.py", repo / "src" / "grammatic" / "__init__.py")

    return repo


def test_complete_workflow(test_repo: Path) -> None:
    subprocess.run(["just", "init"], check=True, capture_output=True, cwd=test_repo)
    subprocess.run(
        ["just", "--justfile", str(test_repo / "justfile"), "new-grammar", "demo"],
        check=True,
        capture_output=True,
        cwd=test_repo.parent,
    )
    subprocess.run(["just", "generate", "demo"], check=True, capture_output=True, cwd=test_repo)

    grammar_dir = test_repo / "grammars" / "demo"
    subprocess.run(["git", "init"], cwd=grammar_dir, check=True, capture_output=True)
    subprocess.run(["git", "config", "user.name", "Test"], cwd=grammar_dir, check=True, capture_output=True)
    subprocess.run(
        ["git", "config", "user.email", "test@test.com"],
        cwd=grammar_dir,
        check=True,
        capture_output=True,
    )
    subprocess.run(["git", "add", "."], cwd=grammar_dir, check=True, capture_output=True)
    subprocess.run(["git", "commit", "-m", "Initial"], cwd=grammar_dir, check=True, capture_output=True)
    subprocess.run(
        ["git", "remote", "add", "origin", "https://example.com/demo"],
        cwd=grammar_dir,
        check=True,
        capture_output=True,
    )

    subprocess.run(["just", "build", "demo"], check=True, capture_output=True, cwd=test_repo)

    test_file = test_repo / "test_demo.txt"
    test_file.write_text("test line\n")

    subprocess.run(["just", "parse", "demo", str(test_file)], check=True, capture_output=True, cwd=test_repo)
    subprocess.run(["just", "test-grammar", "demo"], check=True, capture_output=True, cwd=test_repo)

    builds_result = subprocess.run(
        ["just", "query-builds-for", "demo"],
        capture_output=True,
        text=True,
        check=True,
        cwd=test_repo,
    )
    assert "demo" in builds_result.stdout

    parses_result = subprocess.run(
        ["just", "query-parses-for", "demo"],
        capture_output=True,
        text=True,
        check=True,
        cwd=test_repo,
    )
    assert "demo" in parses_result.stdout

    subprocess.run(["just", "doctor", "demo"], check=True, capture_output=True, cwd=test_repo)
    subprocess.run(["just", "validate-logs"], check=True, capture_output=True, cwd=test_repo)

    list_result = subprocess.run(
        ["just", "list-grammars"],
        capture_output=True,
        text=True,
        check=True,
        cwd=test_repo,
    )
    assert "demo (built)" in list_result.stdout

    assert (test_repo / "build" / "demo" / "demo.so").exists()
    assert (test_repo / "logs" / "builds.jsonl").exists()
    assert (test_repo / "logs" / "parses.jsonl").exists()

    with (test_repo / "logs" / "builds.jsonl").open(encoding="utf-8") as handle:
        build_entry = json.loads(handle.read().splitlines()[-1])
        assert build_entry["grammar"] == "demo"

    with (test_repo / "logs" / "parses.jsonl").open(encoding="utf-8") as handle:
        parse_entry = json.loads(handle.read().splitlines()[-1])
        assert parse_entry["grammar"] == "demo"




def test_build_fails_fast_when_generate_preconditions_are_missing(test_repo: Path) -> None:
    subprocess.run(["just", "init"], check=True, capture_output=True, cwd=test_repo)
    subprocess.run(
        ["just", "--justfile", str(test_repo / "justfile"), "new-grammar", "broken"],
        check=True,
        capture_output=True,
        cwd=test_repo.parent,
    )

    grammar_dir = test_repo / "grammars" / "broken"
    subprocess.run(["git", "init"], cwd=grammar_dir, check=True, capture_output=True)
    subprocess.run(["git", "config", "user.name", "Test"], cwd=grammar_dir, check=True, capture_output=True)
    subprocess.run(
        ["git", "config", "user.email", "test@test.com"],
        cwd=grammar_dir,
        check=True,
        capture_output=True,
    )
    subprocess.run(["git", "add", "."], cwd=grammar_dir, check=True, capture_output=True)
    subprocess.run(["git", "commit", "-m", "Initial"], cwd=grammar_dir, check=True, capture_output=True)
    subprocess.run(
        ["git", "remote", "add", "origin", "https://example.com/broken"],
        cwd=grammar_dir,
        check=True,
        capture_output=True,
    )

    result = subprocess.run(
        ["just", "build", "broken"],
        capture_output=True,
        text=True,
        cwd=test_repo,
    )

    assert result.returncode != 0
    assert "Run 'tree-sitter generate'" in result.stderr
    assert not (test_repo / "build" / "broken" / "broken.so").exists()
    assert not (test_repo / "logs" / "builds.jsonl").exists()


def test_generate_writes_parser_to_grammar_src_before_build(test_repo: Path) -> None:
    subprocess.run(["just", "init"], check=True, capture_output=True, cwd=test_repo)
    subprocess.run(
        ["just", "--justfile", str(test_repo / "justfile"), "new-grammar", "demo"],
        check=True,
        capture_output=True,
        cwd=test_repo.parent,
    )

    parser_c = test_repo / "grammars" / "demo" / "src" / "parser.c"
    assert not parser_c.exists()

    subprocess.run(["just", "generate", "demo"], check=True, capture_output=True, cwd=test_repo)

    assert parser_c.exists()
    assert not (test_repo / "build" / "demo" / "parser.c").exists()
