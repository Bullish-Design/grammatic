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
