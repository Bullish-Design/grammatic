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
    mkdir -p logs build grammars tests/fixtures schemas
  '';
}
