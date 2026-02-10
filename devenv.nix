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
    venv.enable = true;
    uv.enable = true;
  };

  env = {
    GRAMMATIC_ROOT = builtins.toString ./.;
  };

  enterShell = ''
    echo "Grammatic development environment loaded"
    mkdir -p logs build grammars tests/fixtures schemas
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
