#!/usr/bin/env bash
# Purpose: run the perception through the shared lifecycle contract.
set -euo pipefail
script_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
exec bash "$script_dir/../../scripts/lifecycle.sh" "run" "perception"
