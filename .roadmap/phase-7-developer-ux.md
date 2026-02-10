# Phase 7: Developer Experience

## Scope
Add watch mode for iterative development, grammar template generator, pre-commit hooks, and workflow polish.

## Dependencies
- Phase 1-6 complete (full system functional)

## Deliverables

### 1. Watch Mode & Templates

**Add to `justfile`:**
```makefile
# Watch grammar for changes and rebuild
watch GRAMMAR:
    #!/usr/bin/env bash
    if [ ! -d "grammars/{{GRAMMAR}}" ]; then
        echo "Error: Grammar {{GRAMMAR}} not found" >&2
        exit 1
    fi
    echo "Watching grammars/{{GRAMMAR}}/grammar.js for changes..."
    watchexec --watch grammars/{{GRAMMAR}}/grammar.js \
        --clear \
        --restart \
        -- just rebuild {{GRAMMAR}}

# Create new custom grammar from template
new-grammar NAME:
    #!/usr/bin/env bash
    if [ -d "grammars/{{NAME}}" ]; then
        echo "Error: Grammar {{NAME}} already exists" >&2
        exit 1
    fi
    
    mkdir -p grammars/{{NAME}}/src
    mkdir -p grammars/{{NAME}}/test/corpus
    
    cat > grammars/{{NAME}}/grammar.js << 'EOF'
module.exports = grammar({
  name: '{{NAME}}',
  
  rules: {
    source_file: $ => repeat($._line),
    
    _line: $ => choice(
      $.entry,
      $.comment
    ),
    
    entry: $ => /[^\n]+/,
    
    comment: $ => seq('#', /[^\n]*/)
  }
});
EOF
    
    cat > grammars/{{NAME}}/test/corpus/basic.txt << 'EOF'
==================
Basic entry
==================

sample line

---

(source_file
  (entry))

==================
Comment
==================

# this is a comment

---

(source_file
  (comment))
EOF
    
    cat > grammars/{{NAME}}/README.md << 'EOF'
# {{NAME}} Grammar

Tree-sitter grammar for {{NAME}}.

## Development

```bash
# Generate parser
just generate {{NAME}}

# Build shared library
just build {{NAME}}

# Run corpus tests
just test-grammar {{NAME}}

# Watch for changes
just watch {{NAME}}
```
EOF
    
    echo "Created grammar template: grammars/{{NAME}}"
    echo "Next: cd grammars/{{NAME}} && tree-sitter generate"

# List all available grammars
list-grammars:
    #!/usr/bin/env bash
    if [ ! -d grammars ]; then
        echo "No grammars directory found. Run: just init" >&2
        exit 1
    fi
    echo "Available grammars:"
    for dir in grammars/*/; do
        if [ -d "$dir" ]; then
            grammar=$(basename "$dir")
            if [ -f "build/$grammar.so" ]; then
                echo "  ✓ $grammar (built)"
            else
                echo "  ✗ $grammar (not built)"
            fi
        fi
    done

# Show grammar info
info GRAMMAR:
    #!/usr/bin/env bash
    if [ ! -d "grammars/{{GRAMMAR}}" ]; then
        echo "Error: Grammar {{GRAMMAR}} not found" >&2
        exit 1
    fi
    
    echo "Grammar: {{GRAMMAR}}"
    echo "Path: grammars/{{GRAMMAR}}"
    
    if [ -f "grammars/{{GRAMMAR}}/grammar.js" ]; then
        echo "Grammar file: ✓"
    else
        echo "Grammar file: ✗"
    fi
    
    if [ -f "grammars/{{GRAMMAR}}/src/parser.c" ]; then
        echo "Parser generated: ✓"
    else
        echo "Parser generated: ✗"
    fi
    
    if [ -f "build/{{GRAMMAR}}.so" ]; then
        echo "Built: ✓ (build/{{GRAMMAR}}.so)"
    else
        echo "Built: ✗"
    fi
    
    if [ -d "grammars/{{GRAMMAR}}/test/corpus" ]; then
        test_count=$(find grammars/{{GRAMMAR}}/test/corpus -name "*.txt" | wc -l)
        echo "Corpus tests: $test_count file(s)"
    else
        echo "Corpus tests: none"
    fi
    
    # Check if it's a git submodule
    if git -C grammars/{{GRAMMAR}} rev-parse --git-dir > /dev/null 2>&1; then
        commit=$(git -C grammars/{{GRAMMAR}} rev-parse --short HEAD)
        echo "Git commit: $commit"
        
        if git -C grammars/{{GRAMMAR}} remote get-url origin > /dev/null 2>&1; then
            url=$(git -C grammars/{{GRAMMAR}} remote get-url origin)
            echo "Remote: $url"
        fi
    fi

# Help text
help:
    @just --list
```

### 2. Pre-commit Hooks

**Update `devenv.nix`:**
```nix
{ pkgs, ... }:

{
  packages = with pkgs; [
    tree-sitter
    gcc
    gnumake
    python312
    uv
    jq
    git
    just
    watchexec
  ];
  
  languages.python = {
    enable = true;
    package = pkgs.python312;
  };
  
  env = {
    GRAMMATIC_ROOT = builtins.toString ./.;
  };
  
  enterShell = ''
    echo "Grammatic development environment loaded"
    mkdir -p logs build grammars tests/fixtures
  '';
  
  pre-commit.hooks = {
    validate-jsonl = {
      enable = true;
      name = "Validate JSONL logs";
      entry = "just validate-logs";
      files = "logs/.*\\.jsonl$";
      pass_filenames = false;
    };
    
    check-grammar-tests = {
      enable = true;
      name = "Check grammar corpus tests";
      entry = "${pkgs.bash}/bin/bash -c 'if [ -d grammars ]; then for g in grammars/*/; do if [ -f \"$g/grammar.js\" ] && [ ! -d \"$g/test/corpus\" ]; then echo \"Warning: $g has no corpus tests\"; fi; done; fi; true'";
      pass_filenames = false;
    };
  };
}
```

### 3. Enhanced Error Messages

**File: `scripts/grammar_doctor.py`**
```python
#!/usr/bin/env -S uv run
# /// script
# dependencies = ["pydantic>=2.0"]
# ///
# scripts/grammar_doctor.py

from __future__ import annotations

import subprocess
import sys
from pathlib import Path


def check_grammar(grammar: str) -> list[str]:
    """Check grammar and return list of issues."""
    issues = []
    grammar_dir = Path(f"grammars/{grammar}")

    if not grammar_dir.exists():
        issues.append(f"Grammar directory not found: {grammar_dir}")
        return issues

    # Check grammar.js
    if not (grammar_dir / "grammar.js").exists():
        issues.append("Missing grammar.js")

    # Check if parser generated
    if not (grammar_dir / "src" / "parser.c").exists():
        issues.append("Parser not generated. Run: just generate {grammar}")

    # Check if built
    so_path = Path(f"build/{grammar}.so")
    if not so_path.exists():
        issues.append(f"Grammar not built. Run: just build {grammar}")

    # Check corpus tests
    corpus_dir = grammar_dir / "test" / "corpus"
    if not corpus_dir.exists():
        issues.append("No corpus tests directory")
    elif not list(corpus_dir.glob("*.txt")):
        issues.append("No corpus test files")

    # Check for scanner
    has_c_scanner = (grammar_dir / "src" / "scanner.c").exists()
    has_cpp_scanner = (grammar_dir / "src" / "scanner.cc").exists()

    if not has_c_scanner and not has_cpp_scanner:
        # Check if grammar.js uses externals
        if (grammar_dir / "grammar.js").exists():
            with open(grammar_dir / "grammar.js") as f:
                content = f.read()
                if "externals:" in content:
                    issues.append("Grammar uses externals but no scanner.c/scanner.cc found")

    return issues


def main() -> None:
    if len(sys.argv) < 2:
        print("Usage: grammar_doctor.py GRAMMAR")
        sys.exit(1)

    grammar = sys.argv[1]
    issues = check_grammar(grammar)

    if not issues:
        print(f"✓ Grammar '{grammar}' looks good!")
        sys.exit(0)
    else:
        print(f"Issues found for grammar '{grammar}':")
        for issue in issues:
            print(f"  ✗ {issue}")
        sys.exit(1)


if __name__ == "__main__":
    main()
```

**Add to `justfile`:**
```makefile
# Check grammar for common issues
doctor GRAMMAR:
    python scripts/grammar_doctor.py {{GRAMMAR}}
```

## Verification Tests

**File: `tests/test_developer_ux.py`**
```python
# tests/test_developer_ux.py
from __future__ import annotations

import subprocess
from pathlib import Path

import pytest


class TestNewGrammar:
    def test_creates_template(self, test_repo):
        """Create grammar from template."""
        subprocess.run(["just", "init"], check=True, capture_output=True, cwd=test_repo)

        result = subprocess.run(
            ["just", "new-grammar", "mytest"],
            capture_output=True,
            text=True,
            check=True,
            cwd=test_repo,
        )

        assert (test_repo / "grammars" / "mytest" / "grammar.js").exists()
        assert (test_repo / "grammars" / "mytest" / "test" / "corpus" / "basic.txt").exists()
        assert (test_repo / "grammars" / "mytest" / "README.md").exists()

    def test_prevents_duplicate_grammar(self, test_repo):
        """Prevent creating grammar that exists."""
        subprocess.run(["just", "init"], check=True, capture_output=True, cwd=test_repo)
        (test_repo / "grammars" / "existing").mkdir(parents=True)

        result = subprocess.run(
            ["just", "new-grammar", "existing"],
            capture_output=True,
            text=True,
            cwd=test_repo,
        )

        assert result.returncode == 1
        assert "already exists" in result.stderr

    def test_template_is_valid(self, test_repo):
        """Generated template is valid grammar."""
        subprocess.run(["just", "init"], check=True, capture_output=True, cwd=test_repo)
        subprocess.run(["just", "new-grammar", "valid"], check=True, capture_output=True, cwd=test_repo)

        # Should be able to generate parser
        result = subprocess.run(
            ["just", "generate", "valid"],
            capture_output=True,
            text=True,
            check=True,
            cwd=test_repo,
        )

        assert (test_repo / "grammars" / "valid" / "src" / "parser.c").exists()


class TestListGrammars:
    def test_lists_grammars(self, test_repo):
        """List all grammars with build status."""
        subprocess.run(["just", "init"], check=True, capture_output=True, cwd=test_repo)

        # Create some grammars
        (test_repo / "grammars" / "test1").mkdir(parents=True)
        (test_repo / "grammars" / "test2").mkdir(parents=True)
        (test_repo / "build" / "test1.so").touch()

        result = subprocess.run(
            ["just", "list-grammars"],
            capture_output=True,
            text=True,
            check=True,
            cwd=test_repo,
        )

        assert "test1 (built)" in result.stdout
        assert "test2 (not built)" in result.stdout

    def test_empty_grammars_dir(self, test_repo):
        """Handle empty grammars directory."""
        subprocess.run(["just", "init"], check=True, capture_output=True, cwd=test_repo)

        result = subprocess.run(
            ["just", "list-grammars"],
            capture_output=True,
            text=True,
            check=True,
            cwd=test_repo,
        )

        assert "Available grammars" in result.stdout


class TestGrammarInfo:
    def test_shows_info(self, test_repo):
        """Show detailed grammar info."""
        subprocess.run(["just", "init"], check=True, capture_output=True, cwd=test_repo)

        grammar_dir = test_repo / "grammars" / "test"
        grammar_dir.mkdir(parents=True)
        (grammar_dir / "grammar.js").write_text(
            "module.exports = grammar({ name: 'test', rules: { source_file: $ => /.*/ } });"
        )
        (grammar_dir / "src").mkdir()
        (grammar_dir / "src" / "parser.c").touch()
        (test_repo / "build" / "test.so").touch()

        result = subprocess.run(
            ["just", "info", "test"],
            capture_output=True,
            text=True,
            check=True,
            cwd=test_repo,
        )

        assert "Grammar: test" in result.stdout
        assert "Grammar file: ✓" in result.stdout
        assert "Parser generated: ✓" in result.stdout
        assert "Built: ✓" in result.stdout

    def test_missing_grammar(self, test_repo):
        """Handle missing grammar."""
        subprocess.run(["just", "init"], check=True, capture_output=True, cwd=test_repo)

        result = subprocess.run(
            ["just", "info", "nonexistent"],
            capture_output=True,
            text=True,
            cwd=test_repo,
        )

        assert result.returncode == 1
        assert "not found" in result.stderr


class TestGrammarDoctor:
    def test_healthy_grammar(self, test_repo):
        """Check healthy grammar."""
        subprocess.run(["just", "init"], check=True, capture_output=True, cwd=test_repo)

        grammar_dir = test_repo / "grammars" / "healthy"
        grammar_dir.mkdir(parents=True)
        (grammar_dir / "grammar.js").write_text(
            "module.exports = grammar({ name: 'healthy', rules: { source_file: $ => /.*/ } });"
        )
        (grammar_dir / "src").mkdir()
        (grammar_dir / "src" / "parser.c").touch()
        (grammar_dir / "test" / "corpus").mkdir(parents=True)
        (grammar_dir / "test" / "corpus" / "test.txt").touch()
        (test_repo / "build" / "healthy.so").touch()

        result = subprocess.run(
            ["just", "doctor", "healthy"],
            capture_output=True,
            text=True,
            check=True,
            cwd=test_repo,
        )

        assert "looks good" in result.stdout

    def test_detects_issues(self, test_repo):
        """Detect grammar issues."""
        subprocess.run(["just", "init"], check=True, capture_output=True, cwd=test_repo)

        grammar_dir = test_repo / "grammars" / "broken"
        grammar_dir.mkdir(parents=True)
        (grammar_dir / "grammar.js").touch()

        result = subprocess.run(
            ["just", "doctor", "broken"],
            capture_output=True,
            text=True,
            cwd=test_repo,
        )

        assert result.returncode == 1
        assert "Issues found" in result.stdout


class TestHelp:
    def test_help_target(self, test_repo):
        """Show help text."""
        subprocess.run(["just", "init"], check=True, capture_output=True, cwd=test_repo)

        result = subprocess.run(
            ["just", "help"],
            capture_output=True,
            text=True,
            check=True,
            cwd=test_repo,
        )

        # Should list available recipes
        assert result.returncode == 0
        assert len(result.stdout) > 0
```

## Acceptance Criteria

- [ ] `just new-grammar NAME` creates valid template
- [ ] `just watch GRAMMAR` rebuilds on changes
- [ ] `just list-grammars` shows all grammars with build status
- [ ] `just info GRAMMAR` displays grammar details
- [ ] `just doctor GRAMMAR` checks for common issues
- [ ] `just help` shows available commands
- [ ] Pre-commit hooks validate logs and check for tests
- [ ] All tests pass (`pytest tests/test_developer_ux.py -v`)

## Run Tests

```bash
devenv shell
pytest tests/test_developer_ux.py -v
```

## Final Integration Test

**File: `tests/test_full_workflow.py`**
```python
# tests/test_full_workflow.py
from __future__ import annotations

import json
import subprocess
from pathlib import Path


def test_complete_workflow(test_repo):
    """Test complete workflow from scratch."""
    # Initialize
    subprocess.run(["just", "init"], check=True, capture_output=True, cwd=test_repo)

    # Create new grammar
    subprocess.run(["just", "new-grammar", "demo"], check=True, capture_output=True, cwd=test_repo)

    # Generate parser
    subprocess.run(["just", "generate", "demo"], check=True, capture_output=True, cwd=test_repo)

    # Setup git for grammar
    grammar_dir = test_repo / "grammars" / "demo"
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
        ["git", "remote", "add", "origin", "https://example.com/demo"],
        cwd=grammar_dir,
        check=True,
        capture_output=True
    )

    # Build
    subprocess.run(["just", "build", "demo"], check=True, capture_output=True, cwd=test_repo)

    # Create test file
    test_file = test_repo / "test_demo.txt"
    test_file.write_text("test line\n")

    # Parse
    subprocess.run(
        ["just", "parse", "demo", str(test_file)],
        check=True,
        capture_output=True,
        cwd=test_repo
    )

    # Run corpus tests
    subprocess.run(["just", "test-grammar", "demo"], check=True, capture_output=True, cwd=test_repo)

    # Query logs
    builds_result = subprocess.run(
        ["just", "query-builds-for", "demo"],
        capture_output=True,
        text=True,
        check=True,
        cwd=test_repo
    )
    assert "demo" in builds_result.stdout

    parses_result = subprocess.run(
        ["just", "query-parses-for", "demo"],
        capture_output=True,
        text=True,
        check=True,
        cwd=test_repo
    )
    assert "demo" in parses_result.stdout

    # Doctor check
    subprocess.run(["just", "doctor", "demo"], check=True, capture_output=True, cwd=test_repo)

    # Validate logs
    subprocess.run(["just", "validate-logs"], check=True, capture_output=True, cwd=test_repo)

    # List grammars
    list_result = subprocess.run(
        ["just", "list-grammars"],
        capture_output=True,
        text=True,
        check=True,
        cwd=test_repo
    )
    assert "demo (built)" in list_result.stdout

    # Verify artifacts exist
    assert (test_repo / "build" / "demo.so").exists()
    assert (test_repo / "logs" / "builds.jsonl").exists()
    assert (test_repo / "logs" / "parses.jsonl").exists()

    # Verify log contents
    with open(test_repo / "logs" / "builds.jsonl") as f:
        build_entry = json.loads(f.read())
        assert build_entry["grammar"] == "demo"

    with open(test_repo / "logs" / "parses.jsonl") as f:
        parse_entry = json.loads(f.read())
        assert parse_entry["grammar"] == "demo"
```
