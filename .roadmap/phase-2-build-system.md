# Phase 2: Grammar Build System

## Scope
Implement bash script to compile tree-sitter grammars to shared libraries. Handles scanner detection, compiler selection, and platform-specific flags.

## Dependencies
- Phase 1 complete (environment and data models available)

## Deliverables

### 1. Build Script

**File: `scripts/build_grammar.sh`**
```bash
#!/usr/bin/env bash
# scripts/build_grammar.sh
#
# Compile tree-sitter grammar to shared library
# Usage: build_grammar.sh <grammar_dir> <output_so>

set -euo pipefail

GRAMMAR_DIR=$1
OUTPUT_SO=$2

# Validate inputs
if [ ! -d "$GRAMMAR_DIR/src" ]; then
    echo "Error: $GRAMMAR_DIR/src not found" >&2
    exit 1
fi

if [ ! -f "$GRAMMAR_DIR/src/parser.c" ]; then
    echo "Error: $GRAMMAR_DIR/src/parser.c not found" >&2
    echo "Run 'tree-sitter generate' in $GRAMMAR_DIR first" >&2
    exit 1
fi

# Detect platform
case "$(uname -s)" in
    Linux*)
        LDFLAGS="-shared"
        ;;
    Darwin*)
        LDFLAGS="-dynamiclib"
        ;;
    *)
        echo "Unsupported platform: $(uname -s)" >&2
        exit 1
        ;;
esac

# Detect scanner type (C++ vs C)
if [ -f "$GRAMMAR_DIR/src/scanner.cc" ]; then
    COMPILER="g++"
    SCANNER="$GRAMMAR_DIR/src/scanner.cc"
    echo "Using C++ scanner" >&2
elif [ -f "$GRAMMAR_DIR/src/scanner.c" ]; then
    COMPILER="gcc"
    SCANNER="$GRAMMAR_DIR/src/scanner.c"
    echo "Using C scanner" >&2
else
    COMPILER="gcc"
    SCANNER=""
    echo "No scanner file found (parser only)" >&2
fi

# Create output directory
mkdir -p "$(dirname "$OUTPUT_SO")"

# Compile
echo "Compiling: $GRAMMAR_DIR -> $OUTPUT_SO" >&2
if [ -n "$SCANNER" ]; then
    $COMPILER $LDFLAGS -fPIC -O2 \
        -I"$GRAMMAR_DIR/src" \
        "$GRAMMAR_DIR/src/parser.c" \
        "$SCANNER" \
        -o "$OUTPUT_SO"
else
    $COMPILER $LDFLAGS -fPIC -O2 \
        -I"$GRAMMAR_DIR/src" \
        "$GRAMMAR_DIR/src/parser.c" \
        -o "$OUTPUT_SO"
fi

# Verify output
if [ ! -f "$OUTPUT_SO" ]; then
    echo "Error: Build failed - $OUTPUT_SO not created" >&2
    exit 1
fi

echo "Build successful: $OUTPUT_SO" >&2
```

### 2. Test Fixtures

**File: `tests/fixtures/minimal_grammar/grammar.js`**
```javascript
// tests/fixtures/minimal_grammar/grammar.js
module.exports = grammar({
  name: 'minimal',
  
  rules: {
    source_file: $ => repeat($.line),
    line: $ => /[^\n]+/
  }
});
```

**File: `tests/fixtures/scanner_grammar/grammar.js`**
```javascript
// tests/fixtures/scanner_grammar/grammar.js
module.exports = grammar({
  name: 'scanner_test',
  
  externals: $ => [
    $.custom_token
  ],
  
  rules: {
    source_file: $ => repeat($.item),
    item: $ => choice(
      $.custom_token,
      /[a-z]+/
    )
  }
});
```

**File: `tests/fixtures/scanner_grammar/src/scanner.c`**
```c
// tests/fixtures/scanner_grammar/src/scanner.c
#include <tree_sitter/parser.h>

enum TokenType {
  CUSTOM_TOKEN
};

void *tree_sitter_scanner_test_external_scanner_create() {
  return NULL;
}

void tree_sitter_scanner_test_external_scanner_destroy(void *payload) {}

unsigned tree_sitter_scanner_test_external_scanner_serialize(
  void *payload,
  char *buffer
) {
  return 0;
}

void tree_sitter_scanner_test_external_scanner_deserialize(
  void *payload,
  const char *buffer,
  unsigned length
) {}

bool tree_sitter_scanner_test_external_scanner_scan(
  void *payload,
  TSLexer *lexer,
  const bool *valid_symbols
) {
  return false;
}
```

## Verification Tests

**File: `tests/test_build_script.py`**
```python
# tests/test_build_script.py
from __future__ import annotations

import os
import subprocess
from pathlib import Path

import pytest


@pytest.fixture
def minimal_grammar(tmp_path):
    """Create minimal test grammar."""
    grammar_dir = tmp_path / "minimal"
    grammar_dir.mkdir()
    (grammar_dir / "src").mkdir()
    
    # Copy grammar.js
    src = Path("tests/fixtures/minimal_grammar/grammar.js")
    if src.exists():
        import shutil
        shutil.copy(src, grammar_dir / "grammar.js")
    
    # Generate parser
    subprocess.run(
        ["tree-sitter", "generate"],
        cwd=grammar_dir,
        check=True,
        capture_output=True
    )
    
    return grammar_dir


@pytest.fixture
def scanner_grammar(tmp_path):
    """Create grammar with C scanner."""
    grammar_dir = tmp_path / "scanner_test"
    grammar_dir.mkdir()
    (grammar_dir / "src").mkdir()
    
    # Copy files
    src_dir = Path("tests/fixtures/scanner_grammar")
    if src_dir.exists():
        import shutil
        shutil.copy(src_dir / "grammar.js", grammar_dir / "grammar.js")
        shutil.copy(src_dir / "src" / "scanner.c", grammar_dir / "src" / "scanner.c")
    
    # Generate parser
    subprocess.run(
        ["tree-sitter", "generate"],
        cwd=grammar_dir,
        check=True,
        capture_output=True
    )
    
    return grammar_dir


class TestBuildScript:
    def test_minimal_grammar_build(self, minimal_grammar, tmp_path):
        """Build grammar without scanner."""
        output_so = tmp_path / "minimal.so"
        
        result = subprocess.run(
            ["bash", "scripts/build_grammar.sh", str(minimal_grammar), str(output_so)],
            capture_output=True,
            text=True
        )
        
        assert result.returncode == 0, f"Build failed: {result.stderr}"
        assert output_so.exists()
        assert "Build successful" in result.stderr
    
    def test_scanner_grammar_build(self, scanner_grammar, tmp_path):
        """Build grammar with C scanner."""
        output_so = tmp_path / "scanner_test.so"
        
        result = subprocess.run(
            ["bash", "scripts/build_grammar.sh", str(scanner_grammar), str(output_so)],
            capture_output=True,
            text=True
        )
        
        assert result.returncode == 0, f"Build failed: {result.stderr}"
        assert output_so.exists()
        assert "Using C scanner" in result.stderr
    
    def test_missing_parser_c(self, tmp_path):
        """Fail gracefully when parser.c missing."""
        grammar_dir = tmp_path / "incomplete"
        grammar_dir.mkdir()
        (grammar_dir / "src").mkdir()
        
        output_so = tmp_path / "incomplete.so"
        
        result = subprocess.run(
            ["bash", "scripts/build_grammar.sh", str(grammar_dir), str(output_so)],
            capture_output=True,
            text=True
        )
        
        assert result.returncode == 1
        assert "parser.c not found" in result.stderr
        assert not output_so.exists()
    
    def test_missing_src_dir(self, tmp_path):
        """Fail gracefully when src/ missing."""
        grammar_dir = tmp_path / "nosrc"
        grammar_dir.mkdir()
        
        output_so = tmp_path / "nosrc.so"
        
        result = subprocess.run(
            ["bash", "scripts/build_grammar.sh", str(grammar_dir), str(output_so)],
            capture_output=True,
            text=True
        )
        
        assert result.returncode == 1
        assert "src not found" in result.stderr
    
    def test_creates_output_directory(self, minimal_grammar, tmp_path):
        """Create output directory if it doesn't exist."""
        output_so = tmp_path / "nested" / "deep" / "minimal.so"
        
        result = subprocess.run(
            ["bash", "scripts/build_grammar.sh", str(minimal_grammar), str(output_so)],
            capture_output=True,
            text=True
        )
        
        assert result.returncode == 0
        assert output_so.exists()
        assert output_so.parent.exists()
    
    def test_compiler_detection(self, minimal_grammar, tmp_path):
        """Detect gcc for grammar without scanner."""
        output_so = tmp_path / "minimal.so"
        
        result = subprocess.run(
            ["bash", "scripts/build_grammar.sh", str(minimal_grammar), str(output_so)],
            capture_output=True,
            text=True
        )
        
        assert result.returncode == 0
        # Output should mention using gcc implicitly (no scanner)
        assert "parser only" in result.stderr.lower()
```

## Acceptance Criteria

- [ ] Script executable with proper shebang
- [ ] Compiles parser-only grammars (no scanner)
- [ ] Compiles grammars with C scanner
- [ ] Detects platform (Linux/macOS) and uses correct flags
- [ ] Creates output directory if missing
- [ ] Fails gracefully with clear error messages
- [ ] Output .so file is loadable by tree-sitter
- [ ] All tests pass (`pytest tests/test_build_script.py -v`)

## Run Tests

```bash
devenv shell

# Setup test fixtures
cd tests/fixtures/minimal_grammar
tree-sitter generate
cd ../../..

# Run tests
pytest tests/test_build_script.py -v
```

## Notes

- C++ scanner support (scanner.cc) can be added after verifying C scanner works
- Windows support deferred to future phase
- Script should be idempotent (safe to run multiple times)
