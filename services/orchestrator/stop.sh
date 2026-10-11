#!/usr/bin/env bash
# Purpose: stop the orchestrator through the shared lifecycle contract.
set -euo pipefail
script_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
exec bash "$script_dir/../../scripts/lifecycle.sh" "stop" "orchestrator"
