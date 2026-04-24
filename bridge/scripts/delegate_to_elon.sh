#!/usr/bin/env bash
# delegate_to_elon.sh — Milo → Elon handoff via OpenClaw cron dispatch
#
# Milo calls this via its `exec` tool when the classifier (classify.py)
# returns a governance_class of action / publish / irreversible.
#
# Behavior:
#   1. Classifies the task (via classify.py) if not already classified
#   2. Schedules a one-shot isolated cron job on Elon (agent main)
#   3. Polls cron runs until the job reports "finished"
#   4. Returns the result envelope as JSON on stdout
#   5. Exits 0 on success, non-zero on dispatch or runtime failure
#
# Usage (preferred — task.json on stdin, explicit envelope):
#
#   delegate_to_elon.sh <<'EOF'
#   {
#     "summary": "Research the current BTC spot price",
#     "message": "Return one sentence with the current BTC spot price plus your data source.",
#     "side_effects": [],
#     "targets": [],
#     "tools_requested": [],
#     "timeout_seconds": 600
#   }
#   EOF
#
# Usage (shortcut — single quoted message, no classification):
#
#   delegate_to_elon.sh --message "..." [--timeout 600] [--model provider/id]
#
# Requires: openclaw (on PATH), python3, jq
# Env:      OPENCLAW_BIN  — optional override, defaults to "openclaw"

set -euo pipefail

OPENCLAW_BIN="${OPENCLAW_BIN:-openclaw}"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CLASSIFY="$SCRIPT_DIR/classify.py"
POLL_INTERVAL_SEC=5
DEFAULT_TIMEOUT_SEC=600
DEFAULT_POLL_DEADLINE_SEC=900   # Milo gives up waiting after this; Elon may still complete

timestamp_iso() { date -u +"%Y-%m-%dT%H:%M:%SZ"; }

die() {
  jq -n --arg err "$1" --arg ts "$(timestamp_iso)" \
    '{status:"failed", error:$err, at:$ts}' >&2
  printf '%s\n' "$1" >&2
  exit 1
}

read_task_input() {
  local msg="" timeout="$DEFAULT_TIMEOUT_SEC" model=""
  while [ "$#" -gt 0 ]; do
    case "$1" in
      --message)  msg="$2";     shift 2 ;;
      --timeout)  timeout="$2"; shift 2 ;;
      --model)    model="$2";   shift 2 ;;
      --help|-h)  sed -n '2,40p' "$0"; exit 0 ;;
      *)          die "unknown arg: $1" ;;
    esac
  done
  if [ -n "$msg" ]; then
    jq -n \
      --arg summary  "$msg" \
      --arg message  "$msg" \
      --argjson timeout "$timeout" \
      --arg model    "$model" \
      '{summary:$summary, message:$message, side_effects:[], targets:[], tools_requested:[], timeout_seconds:$timeout, model:$model}'
    return
  fi
  # Stdin path
  local payload
  payload="$(cat)"
  [ -n "$payload" ] || die "no task on stdin and no --message argument"
  jq -e type >/dev/null 2>&1 <<<"$payload" || die "input is not valid JSON"
  printf '%s' "$payload"
}

classify_task() {
  local task_json="$1"
  if [ ! -x "$CLASSIFY" ] && [ ! -r "$CLASSIFY" ]; then
    die "classifier not found at $CLASSIFY"
  fi
  python3 "$CLASSIFY" <<<"$task_json" 2>/dev/null || die "classifier failed"
}

schedule_cron() {
  local message="$1" timeout="$2" model="$3" task_id="$4"
  # Fire in 5 seconds — gives cron time to register
  local fire_at
  fire_at="$(date -u -v+5S +%Y-%m-%dT%H:%M:%SZ 2>/dev/null || date -u -d '+5 seconds' +%Y-%m-%dT%H:%M:%SZ)"
  local name="delegate-$task_id"
  local -a args=(
    cron add
    --agent main
    --at "$fire_at"
    --session isolated
    --message "$message"
    --timeout "$timeout"
    --name "$name"
    --no-deliver
    --delete-after-run
  )
  [ -n "$model" ] && args+=(--model "$model")

  local resp
  resp="$("$OPENCLAW_BIN" "${args[@]}" 2>&1)" || die "cron add failed: $resp"
  local job_id
  job_id="$(jq -r '.id // empty' <<<"$resp" 2>/dev/null)"
  [ -n "$job_id" ] || die "could not extract job id from cron add response: $resp"
  printf '%s' "$job_id"
}

poll_until_finished() {
  local job_id="$1"
  local deadline=$(( SECONDS + DEFAULT_POLL_DEADLINE_SEC ))

  while [ "$SECONDS" -lt "$deadline" ]; do
    local runs
    runs="$("$OPENCLAW_BIN" cron runs --id "$job_id" 2>/dev/null || true)"
    # When --delete-after-run triggers, the runs endpoint may return empty after completion
    local first_entry
    first_entry="$(jq '.entries[0] // empty' <<<"$runs" 2>/dev/null)"
    if [ -n "$first_entry" ] && [ "$first_entry" != "null" ]; then
      local action
      action="$(jq -r '.action // empty' <<<"$first_entry" 2>/dev/null)"
      if [ "$action" = "finished" ]; then
        printf '%s' "$first_entry"
        return 0
      fi
    fi
    sleep "$POLL_INTERVAL_SEC"
  done

  die "poll timeout after ${DEFAULT_POLL_DEADLINE_SEC}s (job $job_id)"
}

main() {
  # Tools we depend on
  command -v python3 >/dev/null 2>&1 || die "python3 required"
  command -v jq >/dev/null 2>&1      || die "jq required"
  command -v "$OPENCLAW_BIN" >/dev/null 2>&1 || die "$OPENCLAW_BIN required on PATH"

  local task; task="$(read_task_input "$@")"
  local classification; classification="$(classify_task "$task")"
  local gclass; gclass="$(jq -r '.governance_class' <<<"$classification")"

  # Info class: don't dispatch at all; return the classifier output and tell Milo
  # to handle directly.
  if [ "$gclass" = "info" ]; then
    jq -n \
      --argjson classification "$classification" \
      --arg status "not_dispatched" \
      --arg note "governance_class=info — Milo handles directly; no Elon dispatch" \
      '{status:$status, note:$note, classification:$classification}'
    return 0
  fi

  local message timeout model task_id
  message="$(jq -r '.message // .summary' <<<"$task")"
  timeout="$(jq -r '.timeout_seconds // 600' <<<"$task")"
  model="$(jq -r '.model // empty' <<<"$task")"
  # Short id for cron name (not the task_id field in handoff envelope)
  task_id="$(jq -r '.task_id // empty' <<<"$task")"
  [ -n "$task_id" ] || task_id="$(date +%s%N | shasum | head -c 10)"

  local job_id; job_id="$(schedule_cron "$message" "$timeout" "$model" "$task_id")"
  local entry;  entry="$(poll_until_finished "$job_id")"

  jq -n \
    --argjson classification "$classification" \
    --arg    job_id          "$job_id" \
    --argjson entry           "$entry" \
    --arg    completed_at    "$(timestamp_iso)" \
    '{
      status:          "dispatched_complete",
      classification:  $classification,
      cron_job_id:     $job_id,
      elon_result: {
        run_status:   $entry.status,
        duration_ms:  $entry.durationMs,
        model:        $entry.model,
        provider:     $entry.provider,
        session_key:  $entry.sessionKey,
        summary:      $entry.summary
      },
      completed_at: $completed_at
    }'
}

main "$@"
