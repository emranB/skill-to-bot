#!/usr/bin/env bash
# Purpose: Run the public human-data comparison in isolated service containers without changing app history.
set -euo pipefail
root="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$root"
output="$root/data/exports/build-04-$(date -u +%Y%m%dT%H%M%SZ)"
mkdir -p "$root/data/exports"
mkdir "$output"
mount="$output"
if command -v cygpath >/dev/null 2>&1; then mount="$(cygpath -w "$output")"; fi
export SOURCE_REVISION="$(git rev-parse HEAD 2>/dev/null || printf unrecorded)"
export SOURCE_TREE_DIRTY=unknown
if git rev-parse --is-inside-work-tree >/dev/null 2>&1; then
  SOURCE_TREE_DIRTY="$(if [[ -n "$(git status --porcelain)" ]]; then printf true; else printf false; fi)"
fi
docker compose build orchestrator simulation
for stage in prepare run; do
  service=orchestrator
  if [[ "$stage" == run ]]; then service=simulation; fi
  MSYS_NO_PATHCONV=1 docker compose run --rm --no-deps \
    -e SOURCE_REVISION -e SOURCE_TREE_DIRTY \
    -e OPENBLAS_NUM_THREADS=1 -e OMP_NUM_THREADS=1 -e MKL_NUM_THREADS=1 \
    -v "$mount:/evaluation" "$service" python evaluate.py "$stage"
done
printf 'Evaluation results: %s/results.json\n' "$output"
