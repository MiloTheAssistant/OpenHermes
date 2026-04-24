#!/usr/bin/env bash
# Unified Docker log collector for OpenHermes containers.
# TEMPLATE USAGE: tails milo, elon, and openhermes_proxy and writes a merged stream to stdout.
# Run examples: ./scripts/observability/log-collector.sh or SIEM_ENDPOINT=https://siem.example/ingest ./scripts/observability/log-collector.sh
# Exit codes: 0 on clean shutdown, 1 on dependency or docker inspection failure at startup.

set -euo pipefail

CONTAINERS=("milo" "elon" "openhermes_proxy")
WORKER_PIDS=()
SHUTDOWN=0

timestamp() {
  date -u +"%Y-%m-%dT%H:%M:%SZ"
}

log_stderr() {
  printf '%s [log-collector] %s\n' "$(timestamp)" "$*" >&2
}

require_bin() {
  command -v "$1" >/dev/null 2>&1 || {
    log_stderr "missing required dependency: $1"
    exit 1
  }
}

container_exists() {
  docker inspect "$1" >/dev/null 2>&1
}

forward_to_siem() {
  local line="$1"
  local attempt delay

  if [ -z "${SIEM_ENDPOINT:-}" ]; then
    return 0
  fi

  delay=1
  attempt=1
  while [ "$attempt" -le 3 ]; do
    if curl -fsS \
      -X POST \
      -H "Content-Type: application/x-ndjson" \
      --data-binary "$(printf '%s\n' "$line")" \
      "$SIEM_ENDPOINT" >/dev/null 2>&1; then
      return 0
    fi

    if [ "$attempt" -eq 3 ]; then
      log_stderr "dropping line after SIEM retries exhausted: $line"
      return 1
    fi

    sleep "$delay"
    delay=$((delay * 2))
    attempt=$((attempt + 1))
  done

  return 1
}

emit_line() {
  local formatted="$1"

  printf '%s\n' "$formatted"
  forward_to_siem "$formatted" || true
}

format_json_line() {
  local ts="$1"
  local container="$2"
  local raw_line="$3"

  printf '%s' "$raw_line" | jq -c --arg ts "$ts" --arg container "$container" '
    if type == "object" then
      {ts: $ts, container: $container} + .
    else
      error("log line must be a JSON object")
    end
  ' 2>/dev/null
}

process_log_line() {
  local container="$1"
  local raw_line="$2"
  local ts merged

  ts="$(timestamp)"
  if [[ "$raw_line" == \{* ]]; then
    if merged="$(format_json_line "$ts" "$container" "$raw_line")"; then
      emit_line "$ts [$container] $merged"
      return 0
    fi
  fi

  emit_line "$ts [$container] $raw_line"
}

stream_container() {
  local container="$1"
  local docker_rc

  while [ "$SHUTDOWN" -eq 0 ]; do
    docker logs -f "$container" 2>&1 | while IFS= read -r line; do
      process_log_line "$container" "$line"
    done
    docker_rc=${PIPESTATUS[0]}

    if [ "$SHUTDOWN" -eq 1 ]; then
      return 0
    fi

    if ! container_exists "$container"; then
      log_stderr "container permanently unavailable: $container"
      return 0
    fi

    if [ "$docker_rc" -ne 0 ]; then
      log_stderr "docker logs exited for $container with status $docker_rc; reconnecting in 2 seconds"
      sleep 2
    else
      sleep 2
    fi
  done
}

request_shutdown() {
  SHUTDOWN=1
  log_stderr "shutdown requested; stopping log tails"
  for pid in "${WORKER_PIDS[@]}"; do
    kill "$pid" 2>/dev/null || true
  done
}

main() {
  local container

  require_bin docker
  require_bin jq
  require_bin curl

  for container in "${CONTAINERS[@]}"; do
    if ! container_exists "$container"; then
      log_stderr "container not found: $container"
      exit 1
    fi
  done

  trap request_shutdown INT TERM

  for container in "${CONTAINERS[@]}"; do
    stream_container "$container" &
    WORKER_PIDS+=("$!")
  done

  wait "${WORKER_PIDS[@]}"
}

main "$@"
