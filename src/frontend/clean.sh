#!/usr/bin/env bash
# Purpose: clean the web through the shared lifecycle contract.
set -euo pipefail
script_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
exec bash "$script_dir/../../scripts/lifecycle.sh" "clean" "web"
