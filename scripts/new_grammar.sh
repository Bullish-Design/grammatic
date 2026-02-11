#!/usr/bin/env bash
# scripts/new_grammar.sh
#
# Create a new tree-sitter grammar template.
# Usage: new_grammar.sh <project_root> <grammar_name>

set -euo pipefail

PROJECT_ROOT=$1
NAME=$2
GRAMMAR_DIR="$PROJECT_ROOT/grammars/$NAME"

mkdir -p "$GRAMMAR_DIR/src"
mkdir -p "$GRAMMAR_DIR/test/corpus"

cat <<'EOG' > "$GRAMMAR_DIR/grammar.js"
module.exports = grammar({
  name: '__GRAMMAR_NAME__',

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
EOG

sed -i "s/__GRAMMAR_NAME__/$NAME/g" "$GRAMMAR_DIR/grammar.js"

cat <<'EOC' > "$GRAMMAR_DIR/test/corpus/basic.txt"
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
EOC

cat <<'EOR' > "$GRAMMAR_DIR/README.md"
# __GRAMMAR_NAME__ Grammar

Tree-sitter grammar for __GRAMMAR_NAME__.

## Development

```bash
# Generate parser
just generate __GRAMMAR_NAME__

# Build shared library
just build __GRAMMAR_NAME__

# Run corpus tests
just test-grammar __GRAMMAR_NAME__

# Watch for changes
just watch __GRAMMAR_NAME__
```
EOR

sed -i "s/__GRAMMAR_NAME__/$NAME/g" "$GRAMMAR_DIR/README.md"

echo "Created grammar template: grammars/$NAME"
echo "Next: cd grammars/$NAME && tree-sitter generate"
