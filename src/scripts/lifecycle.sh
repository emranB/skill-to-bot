#!/usr/bin/env bash
# Purpose: Apply consistent, project-scoped Docker Compose lifecycle operations.
set -euo pipefail
project_root="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$project_root"
action="${1:?Lifecycle action required}"
service="${2:-}"
for location in . src/backend/simulation src/backend/orchestrator src/frontend; do
  if [[ ! -f "$location/.env" ]]; then
    cp "$location/.env.example" "$location/.env"
  fi
done
compose() { docker compose -p skill-to-bot "$@"; }
remove_containers() {
  if [[ -n "$service" ]]; then
    compose stop "$service"
    compose rm -f "$service"
  else
    compose down
  fi
}
targets=()
if [[ -n "$service" ]]; then
  case "$service" in simulation|orchestrator|web) targets=("$service");; *) exit 2;; esac
fi
case "$action" in
  build-and-run)
    remove_containers
    compose up -d --build --wait --wait-timeout 240 "${targets[@]}"
    ;;
  run) compose up -d --wait --wait-timeout 240 "${targets[@]}";;
  stop) compose stop "${targets[@]}";;
  clean)
    remove_containers
    ;;
  *) printf 'Unknown lifecycle action: %s\n' "$action" >&2; exit 2;;
esac
if [[ "$action" == run || "$action" == build-and-run ]]; then
  compose ps "${targets[@]}"
  if [[ -z "$service" ]]; then printf 'skill-to-bot: http://localhost:%s\n' "${WEB_PORT:-$(sed -n 's/^WEB_PORT=//p' .env)}"; fi
fi
