#!/usr/bin/env bash
# Purpose: stop the complete skill-to-bot system through the shared lifecycle contract.
set -euo pipefail
script_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
exec bash "$script_dir/src/scripts/lifecycle.sh" "stop" ""
