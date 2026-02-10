// tests/fixtures/minimal_grammar/grammar.js
module.exports = grammar({
  name: 'minimal',

  rules: {
    source_file: $ => repeat($.line),
    line: $ => /[^\n]+/
  }
});
