# Phase 4: Core Justfile Targets

## Scope
Implement basic justfile workflow: init, add-grammar, generate, build, and supporting utilities.

## Dependencies
- Phase 1 complete (environment)
- Phase 2 complete (build script)
- Phase 3 complete (log writer)

## Deliverables

### 1. Core Justfile

**File: `justfile`**
```makefile
# justfile
set shell := ["bash", "-euo", "pipefail", "-c"]

# Initialize grammatic workspace
init:
    #!/usr/bin/env bash
    mkdir -p grammars build logs schemas tests/fixtures
    git submodule init
    echo "Grammatic initialized"
    echo "Add grammars with: just add-grammar NAME URL"

# Add grammar as git submodule
add-grammar NAME URL:
    #!/usr/bin/env bash
    if [ -d "grammars/{{NAME}}" ]; then
        echo "Error: Grammar {{NAME}} already exists" >&2
        exit 1
    fi
    git submodule add {{URL}} grammars/{{NAME}}
    echo "Added grammar: {{NAME}}"
    echo "Next: just generate {{NAME}}"

# Update all grammar submodules to latest remote
update-grammars:
    git submodule update --remote --merge

# Generate parser.c from grammar.js
generate GRAMMAR:
    #!/usr/bin/env bash
    if [ ! -d "grammars/{{GRAMMAR}}" ]; then
        echo "Error: Grammar {{GRAMMAR}} not found" >&2
        exit 1
    fi
    cd grammars/{{GRAMMAR}} && tree-sitter generate
    echo "Generated parser for {{GRAMMAR}}"

# Build grammar to shared library
build GRAMMAR:
    #!/usr/bin/env bash
    START=$(date +%s%3N)
    
    # Ensure parser.c exists
    if [ ! -f "grammars/{{GRAMMAR}}/src/parser.c" ]; then
        echo "Error: parser.c not found. Run: just generate {{GRAMMAR}}" >&2
        exit 1
    fi
    
    # Compile
    bash scripts/build_grammar.sh grammars/{{GRAMMAR}} build/{{GRAMMAR}}.so
    
    END=$(date +%s%3N)
    
    # Extract metadata
    COMMIT=$(git -C grammars/{{GRAMMAR}} rev-parse HEAD)
    REPO_URL=$(git -C grammars/{{GRAMMAR}} config --get remote.origin.url)
    TS_VERSION=$(tree-sitter --version | head -n1 | awk '{print $2}')
    
    # Log build event
    python scripts/log_writer.py build \
        --grammar {{GRAMMAR}} \
        --commit "$COMMIT" \
        --repo-url "$REPO_URL" \
        --so-path build/{{GRAMMAR}}.so \
        --build-time $((END - START)) \
        --tree-sitter-version "$TS_VERSION" \
        >> logs/builds.jsonl
    
    echo "Built: build/{{GRAMMAR}}.so"

# Full rebuild cycle (generate + build)
rebuild GRAMMAR: (generate GRAMMAR) (build GRAMMAR)

# Clean build artifacts
clean:
    rm -rf build/*.so

# Clean everything including logs
clean-all: clean
    rm -rf logs/*.jsonl
```

## Verification Tests

**File: `tests/test_justfile_core.py`**
```python
# tests/test_justfile_core.py
from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pytest


@pytest.fixture
def test_repo(tmp_path, monkeypatch):
    """Create test repository with git."""
    repo = tmp_path / "test_repo"
    repo.mkdir()
    monkeypatch.chdir(repo)
    
    # Initialize git
    subprocess.run(["git", "init"], check=True, capture_output=True)
    subprocess.run(["git", "config", "user.name", "Test"], check=True, capture_output=True)
    subprocess.run(["git", "config", "user.email", "test@test.com"], check=True, capture_output=True)
    
    # Copy justfile and scripts
    import shutil
    shutil.copy(Path.cwd().parent / "justfile", repo / "justfile")
    (repo / "scripts").mkdir()
    shutil.copy(Path.cwd().parent / "scripts" / "build_grammar.sh", repo / "scripts" / "build_grammar.sh")
    shutil.copy(Path.cwd().parent / "scripts" / "log_writer.py", repo / "scripts" / "log_writer.py")
    (repo / "src" / "grammatic").mkdir(parents=True)
    shutil.copy(
        Path.cwd().parent / "src" / "grammatic" / "models.py",
        repo / "src" / "grammatic" / "models.py"
    )
    (repo / "src" / "grammatic" / "__init__.py").touch()
    
    return repo


class TestJustInit:
    def test_creates_directories(self, test_repo):
        """Init creates required directories."""
        result = subprocess.run(["just", "init"], capture_output=True, text=True, check=True)
        
        assert (test_repo / "grammars").exists()
        assert (test_repo / "build").exists()
        assert (test_repo / "logs").exists()
        assert (test_repo / "schemas").exists()
        assert (test_repo / "tests/fixtures").exists()
        assert "initialized" in result.stdout.lower()
    
    def test_idempotent(self, test_repo):
        """Can run init multiple times."""
        subprocess.run(["just", "init"], check=True, capture_output=True)
        result = subprocess.run(["just", "init"], capture_output=True, text=True, check=True)
        assert result.returncode == 0


class TestJustAddGrammar:
    def test_adds_submodule(self, test_repo):
        """Add grammar as git submodule."""
        subprocess.run(["just", "init"], check=True, capture_output=True)
        
        # Create a mock grammar repo
        grammar_repo = test_repo.parent / "mock_grammar"
        grammar_repo.mkdir()
        subprocess.run(["git", "init"], cwd=grammar_repo, check=True, capture_output=True)
        (grammar_repo / "grammar.js").write_text("module.exports = grammar({ name: 'mock', rules: {} });")
        subprocess.run(["git", "add", "."], cwd=grammar_repo, check=True, capture_output=True)
        subprocess.run(
            ["git", "commit", "-m", "Initial"],
            cwd=grammar_repo,
            check=True,
            capture_output=True
        )
        
        result = subprocess.run(
            ["just", "add-grammar", "mock", str(grammar_repo)],
            capture_output=True,
            text=True,
            check=True
        )
        
        assert (test_repo / "grammars" / "mock").exists()
        assert "Added grammar: mock" in result.stdout
    
    def test_prevents_duplicate(self, test_repo):
        """Prevent adding same grammar twice."""
        subprocess.run(["just", "init"], check=True, capture_output=True)
        (test_repo / "grammars" / "test").mkdir(parents=True)
        
        result = subprocess.run(
            ["just", "add-grammar", "test", "https://example.com"],
            capture_output=True,
            text=True
        )
        
        assert result.returncode == 1
        assert "already exists" in result.stderr


class TestJustGenerate:
    def test_generates_parser(self, test_repo):
        """Generate parser.c from grammar.js."""
        subprocess.run(["just", "init"], check=True, capture_output=True)
        
        # Create minimal grammar
        grammar_dir = test_repo / "grammars" / "test"
        grammar_dir.mkdir(parents=True)
        (grammar_dir / "grammar.js").write_text(
            "module.exports = grammar({ name: 'test', rules: { source_file: $ => /.*/ } });"
        )
        
        result = subprocess.run(
            ["just", "generate", "test"],
            capture_output=True,
            text=True,
            check=True
        )
        
        assert (grammar_dir / "src" / "parser.c").exists()
        assert "Generated parser" in result.stdout
    
    def test_missing_grammar(self, test_repo):
        """Fail gracefully if grammar doesn't exist."""
        subprocess.run(["just", "init"], check=True, capture_output=True)
        
        result = subprocess.run(
            ["just", "generate", "nonexistent"],
            capture_output=True,
            text=True
        )
        
        assert result.returncode == 1
        assert "not found" in result.stderr


class TestJustBuild:
    def test_builds_grammar(self, test_repo):
        """Build grammar to .so file."""
        subprocess.run(["just", "init"], check=True, capture_output=True)
        
        # Create and generate grammar
        grammar_dir = test_repo / "grammars" / "test"
        grammar_dir.mkdir(parents=True)
        (grammar_dir / "grammar.js").write_text(
            "module.exports = grammar({ name: 'test', rules: { source_file: $ => /.*/ } });"
        )
        
        # Initialize git in grammar dir for commit hash
        subprocess.run(["git", "init"], cwd=grammar_dir, check=True, capture_output=True)
        subprocess.run(["git", "config", "user.name", "Test"], cwd=grammar_dir, check=True, capture_output=True)
        subprocess.run(
            ["git", "config", "user.email", "test@test.com"],
            cwd=grammar_dir,
            check=True,
            capture_output=True
        )
        subprocess.run(["git", "add", "."], cwd=grammar_dir, check=True, capture_output=True)
        subprocess.run(["git", "commit", "-m", "Initial"], cwd=grammar_dir, check=True, capture_output=True)
        subprocess.run(
            ["git", "remote", "add", "origin", "https://example.com/test"],
            cwd=grammar_dir,
            check=True,
            capture_output=True
        )
        
        subprocess.run(["just", "generate", "test"], check=True, capture_output=True)
        
        result = subprocess.run(
            ["just", "build", "test"],
            capture_output=True,
            text=True,
            check=True
        )
        
        assert (test_repo / "build" / "test.so").exists()
        assert (test_repo / "logs" / "builds.jsonl").exists()
        assert "Built:" in result.stdout
    
    def test_logs_build_event(self, test_repo):
        """Build logs event to builds.jsonl."""
        subprocess.run(["just", "init"], check=True, capture_output=True)
        
        grammar_dir = test_repo / "grammars" / "test"
        grammar_dir.mkdir(parents=True)
        (grammar_dir / "grammar.js").write_text(
            "module.exports = grammar({ name: 'test', rules: { source_file: $ => /.*/ } });"
        )
        
        # Setup git
        subprocess.run(["git", "init"], cwd=grammar_dir, check=True, capture_output=True)
        subprocess.run(["git", "config", "user.name", "Test"], cwd=grammar_dir, check=True, capture_output=True)
        subprocess.run(
            ["git", "config", "user.email", "test@test.com"],
            cwd=grammar_dir,
            check=True,
            capture_output=True
        )
        subprocess.run(["git", "add", "."], cwd=grammar_dir, check=True, capture_output=True)
        subprocess.run(["git", "commit", "-m", "Initial"], cwd=grammar_dir, check=True, capture_output=True)
        subprocess.run(
            ["git", "remote", "add", "origin", "https://example.com/test"],
            cwd=grammar_dir,
            check=True,
            capture_output=True
        )
        
        subprocess.run(["just", "generate", "test"], check=True, capture_output=True)
        subprocess.run(["just", "build", "test"], check=True, capture_output=True)
        
        # Read log
        with open(test_repo / "logs" / "builds.jsonl") as f:
            entry = json.loads(f.read())
        
        assert entry["event_type"] == "build"
        assert entry["grammar"] == "test"
        assert entry["build_success"] is True
        assert "commit" in entry
        assert "build_time_ms" in entry


class TestJustRebuild:
    def test_rebuild_generates_and_builds(self, test_repo):
        """Rebuild runs generate then build."""
        subprocess.run(["just", "init"], check=True, capture_output=True)
        
        grammar_dir = test_repo / "grammars" / "test"
        grammar_dir.mkdir(parents=True)
        (grammar_dir / "grammar.js").write_text(
            "module.exports = grammar({ name: 'test', rules: { source_file: $ => /.*/ } });"
        )
        
        # Setup git
        subprocess.run(["git", "init"], cwd=grammar_dir, check=True, capture_output=True)
        subprocess.run(["git", "config", "user.name", "Test"], cwd=grammar_dir, check=True, capture_output=True)
        subprocess.run(
            ["git", "config", "user.email", "test@test.com"],
            cwd=grammar_dir,
            check=True,
            capture_output=True
        )
        subprocess.run(["git", "add", "."], cwd=grammar_dir, check=True, capture_output=True)
        subprocess.run(["git", "commit", "-m", "Initial"], cwd=grammar_dir, check=True, capture_output=True)
        subprocess.run(
            ["git", "remote", "add", "origin", "https://example.com/test"],
            cwd=grammar_dir,
            check=True,
            capture_output=True
        )
        
        result = subprocess.run(
            ["just", "rebuild", "test"],
            capture_output=True,
            text=True,
            check=True
        )
        
        assert (grammar_dir / "src" / "parser.c").exists()
        assert (test_repo / "build" / "test.so").exists()


class TestJustClean:
    def test_clean_removes_so_files(self, test_repo):
        """Clean removes .so files."""
        subprocess.run(["just", "init"], check=True, capture_output=True)
        (test_repo / "build" / "test.so").touch()
        
        subprocess.run(["just", "clean"], check=True, capture_output=True)
        
        assert not (test_repo / "build" / "test.so").exists()
    
    def test_clean_all_removes_logs(self, test_repo):
        """Clean-all removes logs too."""
        subprocess.run(["just", "init"], check=True, capture_output=True)
        (test_repo / "logs" / "builds.jsonl").touch()
        
        subprocess.run(["just", "clean-all"], check=True, capture_output=True)
        
        assert not (test_repo / "logs" / "builds.jsonl").exists()
```

## Acceptance Criteria

- [ ] `just init` creates all required directories
- [ ] `just add-grammar` adds git submodule
- [ ] `just generate` creates parser.c
- [ ] `just build` compiles .so and logs to builds.jsonl
- [ ] `just rebuild` combines generate and build
- [ ] `just clean` removes .so files
- [ ] `just clean-all` removes .so and logs
- [ ] All tests pass (`pytest tests/test_justfile_core.py -v`)

## Run Tests

```bash
devenv shell
pytest tests/test_justfile_core.py -v
```
