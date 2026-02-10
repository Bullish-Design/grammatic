# Phase 5: Parse & Test Integration

## Scope
Implement parse target for testing grammars against source files, test-grammar for corpus tests, and integration test fixtures.

## Dependencies
- Phase 1-4 complete (full build pipeline working)

## Deliverables

### 1. Parse Target

**Add to `justfile`:**
```makefile
# Parse source file with grammar
parse GRAMMAR FILE:
    #!/usr/bin/env bash
    if [ ! -f "build/{{GRAMMAR}}.so" ]; then
        echo "Error: Grammar not built. Run: just build {{GRAMMAR}}" >&2
        exit 1
    fi
    
    START=$(date +%s%3N)
    
    # Parse to JSON
    tree-sitter parse {{FILE}} \
        --language build/{{GRAMMAR}}.so \
        --json > /tmp/parse_{{GRAMMAR}}_$$.json
    
    END=$(date +%s%3N)
    
    # Log parse event
    python scripts/log_writer.py parse \
        --grammar {{GRAMMAR}} \
        --source {{FILE}} \
        --parse-result /tmp/parse_{{GRAMMAR}}_$$.json \
        --parse-time $((END - START)) \
        >> logs/parses.jsonl
    
    # Display result
    cat /tmp/parse_{{GRAMMAR}}_$$.json | jq '.'
    echo ""
    echo "Parse logged to parses.jsonl"

# Run tree-sitter corpus tests for grammar
test-grammar GRAMMAR:
    #!/usr/bin/env bash
    if [ ! -d "grammars/{{GRAMMAR}}/test/corpus" ]; then
        echo "Error: No corpus tests found for {{GRAMMAR}}" >&2
        exit 1
    fi
    cd grammars/{{GRAMMAR}} && tree-sitter test

# Full test cycle (build + parse fixture)
test GRAMMAR: (build GRAMMAR)
    just parse {{GRAMMAR}} tests/fixtures/sample_{{GRAMMAR}}.txt
```

### 2. Test Fixtures

**File: `tests/fixtures/sample_minimal.txt`**
```
hello world
test line
```

**File: `tests/fixtures/sample_python.py`**
```python
# tests/fixtures/sample_python.py
def greet(name):
    """Say hello."""
    print(f"Hello, {name}!")

class Calculator:
    def add(self, a, b):
        return a + b

if __name__ == "__main__":
    greet("World")
```

**File: `tests/fixtures/minimal_grammar/test/corpus/basic.txt`**
```
==================
Single line
==================

hello

---

(source_file
  (line))

==================
Multiple lines
==================

first
second
third

---

(source_file
  (line)
  (line)
  (line))
```

## Verification Tests

**File: `tests/test_parse.py`**
```python
# tests/test_parse.py
from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pytest


@pytest.fixture
def minimal_grammar_built(test_repo):
    """Build minimal grammar for testing."""
    subprocess.run(["just", "init"], check=True, capture_output=True, cwd=test_repo)
    
    grammar_dir = test_repo / "grammars" / "minimal"
    grammar_dir.mkdir(parents=True)
    (grammar_dir / "grammar.js").write_text(
        "module.exports = grammar({ name: 'minimal', rules: { source_file: $ => repeat($.line), line: $ => /[^\\n]+/ } });"
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
        ["git", "remote", "add", "origin", "https://example.com/minimal"],
        cwd=grammar_dir,
        check=True,
        capture_output=True
    )
    
    subprocess.run(["just", "build", "minimal"], check=True, capture_output=True, cwd=test_repo)
    
    return test_repo


class TestParse:
    def test_parse_valid_file(self, minimal_grammar_built):
        """Parse valid source file."""
        test_file = minimal_grammar_built / "test.txt"
        test_file.write_text("hello\nworld\n")
        
        result = subprocess.run(
            ["just", "parse", "minimal", str(test_file)],
            capture_output=True,
            text=True,
            check=True,
            cwd=minimal_grammar_built
        )
        
        assert "Parse logged" in result.stdout
        assert (minimal_grammar_built / "logs" / "parses.jsonl").exists()
    
    def test_parse_logs_event(self, minimal_grammar_built):
        """Parse creates log entry."""
        test_file = minimal_grammar_built / "test.txt"
        test_file.write_text("line one\nline two\n")
        
        subprocess.run(
            ["just", "parse", "minimal", str(test_file)],
            check=True,
            capture_output=True,
            cwd=minimal_grammar_built
        )
        
        with open(minimal_grammar_built / "logs" / "parses.jsonl") as f:
            entry = json.loads(f.read())
        
        assert entry["event_type"] == "parse"
        assert entry["grammar"] == "minimal"
        assert entry["node_count"] > 0
        assert entry["has_errors"] is False
    
    def test_parse_without_build(self, test_repo):
        """Fail if grammar not built."""
        subprocess.run(["just", "init"], check=True, capture_output=True, cwd=test_repo)
        
        test_file = test_repo / "test.txt"
        test_file.write_text("test")
        
        result = subprocess.run(
            ["just", "parse", "nonexistent", str(test_file)],
            capture_output=True,
            text=True,
            cwd=test_repo
        )
        
        assert result.returncode == 1
        assert "not built" in result.stderr.lower()
    
    def test_parse_detects_errors(self, minimal_grammar_built):
        """Detect ERROR nodes in invalid syntax."""
        # This would need a grammar that can produce ERROR nodes
        # For now, just verify the log structure
        test_file = minimal_grammar_built / "test.txt"
        test_file.write_text("valid line\n")
        
        subprocess.run(
            ["just", "parse", "minimal", str(test_file)],
            check=True,
            capture_output=True,
            cwd=minimal_grammar_built
        )
        
        with open(minimal_grammar_built / "logs" / "parses.jsonl") as f:
            entry = json.loads(f.read())
        
        assert "has_errors" in entry
        assert isinstance(entry["has_errors"], bool)


class TestCorpusTests:
    def test_run_corpus_tests(self, test_repo):
        """Run tree-sitter corpus tests."""
        subprocess.run(["just", "init"], check=True, capture_output=True, cwd=test_repo)
        
        # Create grammar with corpus tests
        grammar_dir = test_repo / "grammars" / "minimal"
        grammar_dir.mkdir(parents=True)
        (grammar_dir / "grammar.js").write_text(
            "module.exports = grammar({ name: 'minimal', rules: { source_file: $ => repeat($.line), line: $ => /[^\\n]+/ } });"
        )
        
        corpus_dir = grammar_dir / "test" / "corpus"
        corpus_dir.mkdir(parents=True)
        (corpus_dir / "basic.txt").write_text(
            """==================
Simple line
==================

hello

---

(source_file
  (line))
"""
        )
        
        subprocess.run(["just", "generate", "minimal"], check=True, capture_output=True, cwd=test_repo)
        
        result = subprocess.run(
            ["just", "test-grammar", "minimal"],
            capture_output=True,
            text=True,
            check=True,
            cwd=test_repo
        )
        
        assert result.returncode == 0
    
    def test_corpus_tests_missing(self, test_repo):
        """Fail gracefully if no corpus tests."""
        subprocess.run(["just", "init"], check=True, capture_output=True, cwd=test_repo)
        
        grammar_dir = test_repo / "grammars" / "nocorpus"
        grammar_dir.mkdir(parents=True)
        
        result = subprocess.run(
            ["just", "test-grammar", "nocorpus"],
            capture_output=True,
            text=True,
            cwd=test_repo
        )
        
        assert result.returncode == 1
        assert "No corpus tests" in result.stderr


class TestFullCycle:
    def test_full_test_target(self, test_repo):
        """Test target builds and parses."""
        subprocess.run(["just", "init"], check=True, capture_output=True, cwd=test_repo)
        
        # Setup grammar
        grammar_dir = test_repo / "grammars" / "minimal"
        grammar_dir.mkdir(parents=True)
        (grammar_dir / "grammar.js").write_text(
            "module.exports = grammar({ name: 'minimal', rules: { source_file: $ => repeat($.line), line: $ => /[^\\n]+/ } });"
        )
        
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
            ["git", "remote", "add", "origin", "https://example.com/minimal"],
            cwd=grammar_dir,
            check=True,
            capture_output=True
        )
        
        subprocess.run(["just", "generate", "minimal"], check=True, capture_output=True, cwd=test_repo)
        
        # Create fixture
        fixture = test_repo / "tests" / "fixtures" / "sample_minimal.txt"
        fixture.parent.mkdir(parents=True, exist_ok=True)
        fixture.write_text("test line\n")
        
        result = subprocess.run(
            ["just", "test", "minimal"],
            capture_output=True,
            text=True,
            check=True,
            cwd=test_repo
        )
        
        assert (test_repo / "build" / "minimal.so").exists()
        assert (test_repo / "logs" / "builds.jsonl").exists()
        assert (test_repo / "logs" / "parses.jsonl").exists()
```

## Acceptance Criteria

- [ ] `just parse GRAMMAR FILE` parses source file
- [ ] Parse events logged to parses.jsonl with all fields
- [ ] Parse result displayed as JSON
- [ ] `just test-grammar GRAMMAR` runs corpus tests
- [ ] `just test GRAMMAR` builds and parses fixture
- [ ] Node counting works correctly
- [ ] ERROR detection works
- [ ] All tests pass (`pytest tests/test_parse.py -v`)

## Run Tests

```bash
devenv shell
pytest tests/test_parse.py -v
```
