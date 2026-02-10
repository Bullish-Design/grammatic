#!/usr/bin/env bash
set -euo pipefail

case "$(uname -s)" in
    Linux*)
        echo "-shared"
        ;;
    Darwin*)
        echo "-dynamiclib"
        ;;
    *)
        echo "Unsupported platform: $(uname -s)" >&2
        exit 1
        ;;
esac
