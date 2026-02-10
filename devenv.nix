{ pkgs, ... }:

{
  packages = with pkgs; [
    tree-sitter
    gcc
    gnumake
    uv
    jq
    git
    just
    watchexec
  ];

  languages.python = {
    enable = true;
    version = "3.13";
    venv.enable = true;
    uv.enable = true;
  };

  env = {
    GRAMMATIC_ROOT = "./.";
  };

  enterShell = ''
    echo "Grammatic development environment loaded"
    mkdir -p logs build grammars tests/fixtures schemas
  '';
}
