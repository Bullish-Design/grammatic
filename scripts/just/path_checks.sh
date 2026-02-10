#!/usr/bin/env bash
set -euo pipefail

usage() {
  echo "Usage: $0 <missing|dir|file> <path> <error-message>" >&2
  exit 2
}

[ "$#" -eq 3 ] || usage

check_type="$1"
path="$2"
error_message="$3"

case "$check_type" in
  missing)
    if [ -e "$path" ]; then
      echo "$error_message" >&2
      exit 1
    fi
    ;;
  dir)
    if [ ! -d "$path" ]; then
      echo "$error_message" >&2
      exit 1
    fi
    ;;
  file)
    if [ ! -f "$path" ]; then
      echo "$error_message" >&2
      exit 1
    fi
    ;;
  *)
    usage
    ;;
esac
