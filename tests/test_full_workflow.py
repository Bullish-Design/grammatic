from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path

import pytest

from grammatic.contracts import BuildRequest, DoctorRequest, GenerateRequest, ParseRequest, TestGrammarRequest
from grammatic.logs import LogRepository
from grammatic.workflows import handle_build, handle_doctor, handle_generate, handle_parse, handle_test_grammar

PROJECT_ROOT = Path(__file__).resolve().parents[1]


def require_toolchain() -> None:
    """Skip tests if required tools are not available."""
    missing = [tool for tool in ("git", "tree-sitter", "gcc") if shutil.which(tool) is None]
    if missing:
        pytest.skip(f"Required tool(s) unavailable in PATH: {', '.join(missing)}")


def setup_test_grammar(repo: Path, grammar_name: str) -> Path:
    """Create a test grammar from template."""
    require_toolchain()

    grammar_dir = repo / "grammars" / grammar_name
    grammar_dir.mkdir(parents=True)

    # Use new_grammar.sh to create the template
    subprocess.run(
        [str(PROJECT_ROOT / "scripts" / "new_grammar.sh"), str(repo), grammar_name],
        check=True,
        capture_output=True,
    )

    # Initialize git repo for the grammar
    subprocess.run(["git", "init"], cwd=grammar_dir, check=True, capture_output=True)
    subprocess.run(["git", "config", "user.name", "Test"], cwd=grammar_dir, check=True, capture_output=True)
    subprocess.run(["git", "config", "user.email", "test@test.com"], cwd=grammar_dir, check=True, capture_output=True)
    subprocess.run(["git", "add", "."], cwd=grammar_dir, check=True, capture_output=True)
    subprocess.run(["git", "commit", "-m", "Initial"], cwd=grammar_dir, check=True, capture_output=True)
    subprocess.run(
        ["git", "remote", "add", "origin", f"https://example.com/{grammar_name}"],
        cwd=grammar_dir,
        check=True,
        capture_output=True,
    )

    return grammar_dir


@pytest.fixture
def test_repo(tmp_path: Path) -> Path:
    """Create a test repository structure."""
    require_toolchain()

    repo = tmp_path / "test_repo"
    (repo / "grammars").mkdir(parents=True)
    (repo / "build").mkdir(parents=True)
    (repo / "logs").mkdir(parents=True)
    (repo / "scripts").mkdir(parents=True)
    (repo / "tests" / "fixtures").mkdir(parents=True)

    return repo


def test_complete_workflow(test_repo: Path) -> None:
    """Test complete workflow: generate -> build -> parse -> test -> doctor."""
    # Create grammar
    setup_test_grammar(test_repo, "demo")

    # Generate parser
    generate_result = handle_generate(GenerateRequest(grammar="demo", repo_root=test_repo))
    assert generate_result.status == "ok"

    # Build grammar
    build_result = handle_build(BuildRequest(grammar="demo", repo_root=test_repo))
    assert build_result.status == "ok"
    assert build_result.artifact_path.exists()
    assert build_result.artifact_path == test_repo / "build" / "demo" / "demo.so"

    # Parse a test file
    test_file = test_repo / "test_demo.txt"
    test_file.write_text("test line\n")

    parse_result = handle_parse(ParseRequest(grammar="demo", repo_root=test_repo, source=test_file))
    assert parse_result.status == "ok"
    assert parse_result.has_errors is False

    # Run corpus tests
    test_result = handle_test_grammar(TestGrammarRequest(grammar="demo", repo_root=test_repo))
    assert test_result.status == "ok"

    # Run doctor to check for issues
    doctor_result = handle_doctor(DoctorRequest(grammar="demo", repo_root=test_repo))
    assert doctor_result.status == "ok"

    # Verify logs were created
    assert (test_repo / "logs" / "builds.jsonl").exists()
    assert (test_repo / "logs" / "parses.jsonl").exists()

    # Verify log contents
    with (test_repo / "logs" / "builds.jsonl").open(encoding="utf-8") as handle:
        build_entry = json.loads(handle.read().splitlines()[-1])
        assert build_entry["grammar"] == "demo"
        assert build_entry["status"] == "success"

    with (test_repo / "logs" / "parses.jsonl").open(encoding="utf-8") as handle:
        parse_entry = json.loads(handle.read().splitlines()[-1])
        assert parse_entry["grammar"] == "demo"

    # Test log queries
    repo = LogRepository(test_repo)
    builds = list(repo.recent_builds(grammar="demo"))
    assert len(builds) == 1
    assert builds[0].grammar == "demo"

    parses = list(repo.recent_parses(grammar="demo"))
    assert len(parses) == 1
    assert parses[0].grammar == "demo"


def test_build_fails_fast_when_parser_missing(test_repo: Path) -> None:
    """Build fails with clear error when parser.c is missing (generate not run)."""
    setup_test_grammar(test_repo, "broken")

    # Try to build without generating first
    with pytest.raises(Exception) as exc_info:
        handle_build(BuildRequest(grammar="broken", repo_root=test_repo))

    error_message = str(exc_info.value)
    assert "parser.c" in error_message or "generate" in error_message.lower()

    # Verify no build artifact was created
    assert not (test_repo / "build" / "broken" / "broken.so").exists()

    # Verify no log entry was created (or if created, it's a failure)
    builds_log = test_repo / "logs" / "builds.jsonl"
    if builds_log.exists():
        with builds_log.open(encoding="utf-8") as handle:
            for line in handle:
                entry = json.loads(line)
                if entry["grammar"] == "broken":
                    assert entry["status"] == "failure"


def test_generate_writes_parser_to_grammar_src(test_repo: Path) -> None:
    """Generate creates parser.c in grammar/src/ directory."""
    setup_test_grammar(test_repo, "demo")

    parser_c = test_repo / "grammars" / "demo" / "src" / "parser.c"
    assert not parser_c.exists()

    handle_generate(GenerateRequest(grammar="demo", repo_root=test_repo))

    assert parser_c.exists()
    # Verify parser is in grammar dir, not build dir
    assert not (test_repo / "build" / "demo" / "parser.c").exists()


def test_parse_failure_is_logged(test_repo: Path) -> None:
    """Failed parse operations are logged with failure status."""
    setup_test_grammar(test_repo, "demo")
    handle_generate(GenerateRequest(grammar="demo", repo_root=test_repo))
    handle_build(BuildRequest(grammar="demo", repo_root=test_repo))

    missing_file = test_repo / "nonexistent.txt"

    # This should raise an error
    with pytest.raises(Exception):
        handle_parse(ParseRequest(grammar="demo", repo_root=test_repo, source=missing_file))

    # Verify failure was logged
    parses_log = test_repo / "logs" / "parses.jsonl"
    assert parses_log.exists()

    with parses_log.open(encoding="utf-8") as handle:
        entry = json.loads(handle.read().strip().splitlines()[-1])
        assert entry["grammar"] == "demo"
        assert entry["status"] == "failure"


def test_workflow_with_multiple_grammars(test_repo: Path) -> None:
    """Multiple grammars can coexist and be built/tested independently."""
    # Set up two grammars
    setup_test_grammar(test_repo, "grammar_a")
    setup_test_grammar(test_repo, "grammar_b")

    # Generate and build both
    handle_generate(GenerateRequest(grammar="grammar_a", repo_root=test_repo))
    handle_build(BuildRequest(grammar="grammar_a", repo_root=test_repo))

    handle_generate(GenerateRequest(grammar="grammar_b", repo_root=test_repo))
    handle_build(BuildRequest(grammar="grammar_b", repo_root=test_repo))

    # Verify both built
    assert (test_repo / "build" / "grammar_a" / "grammar_a.so").exists()
    assert (test_repo / "build" / "grammar_b" / "grammar_b.so").exists()

    # Verify logs contain both
    repo = LogRepository(test_repo)
    builds = list(repo.recent_builds())
    grammars_built = {build.grammar for build in builds}
    assert "grammar_a" in grammars_built
    assert "grammar_b" in grammars_built


def test_doctor_detects_missing_corpus(test_repo: Path) -> None:
    """Doctor reports when corpus tests are missing or incomplete."""
    setup_test_grammar(test_repo, "demo")
    handle_generate(GenerateRequest(grammar="demo", repo_root=test_repo))
    handle_build(BuildRequest(grammar="demo", repo_root=test_repo))

    # Remove corpus directory
    corpus_dir = test_repo / "grammars" / "demo" / "test" / "corpus"
    if corpus_dir.exists():
        shutil.rmtree(corpus_dir)
        corpus_dir.mkdir(parents=True)

    result = handle_doctor(DoctorRequest(grammar="demo", repo_root=test_repo))

    # Doctor should report issues or warnings about missing corpus
    assert result.status == "error" or len(result.findings) > 0
