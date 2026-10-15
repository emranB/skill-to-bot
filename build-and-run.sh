#!/usr/bin/env bash
# Purpose: build-and-run the complete skill-to-bot system through the shared lifecycle contract.
set -euo pipefail
script_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
exec bash "$script_dir/src/scripts/lifecycle.sh" "build-and-run" ""
