#!/usr/bin/env bash
# audit-checksum.sh — tamper-evidence checksums for governance/audit/
#
# Computes SHA-256 over every *.jsonl in governance/audit/, writes the
# results to governance/audit/checksums.sha256, and stages the file for
# commit. Designed to run weekly (Sunday 00:00 by default) via:
#
#   openclaw cron add --at "0 0 * * 0" --session isolated \
#     --message "bash $OPENHERMES_ROOT/scripts/observability/audit-checksum.sh" \
#     --name "audit-checksum-weekly" --no-deliver
#
# Manual run (for the pre-launch audit):
#
#   OPENHERMES_ROOT=~/repos/OpenHermes ./scripts/observability/audit-checksum.sh
#
# Exit codes:
#   0 — checksums written; tree clean after commit
#   1 — dependency missing, path issue, or git commit failure
#   2 — existing checksum differs from computed (tamper detected)
#
# Env:
#   OPENHERMES_ROOT  — absolute path to OpenHermes working tree
#                      (defaults to the script's grandparent directory)
#   CHECKSUM_FAIL_ON_DRIFT
#                    — if set to "1", tamper detection exits 2 instead
#                      of updating the checksum file (CI-mode)

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
OPENHERMES_ROOT="${OPENHERMES_ROOT:-$(cd "$SCRIPT_DIR/../.." && pwd)}"
AUDIT_DIR="$OPENHERMES_ROOT/governance/audit"
CHECKSUM_FILE="$AUDIT_DIR/checksums.sha256"

timestamp_iso() { date -u +"%Y-%m-%dT%H:%M:%SZ"; }

die() {
  printf '[audit-checksum] %s\n' "$*" >&2
  exit 1
}

require_bin() {
  command -v "$1" >/dev/null 2>&1 || die "missing required dependency: $1"
}

main() {
  require_bin shasum       # BSD (macOS) + Linux both have this
  require_bin git
  require_bin awk
  require_bin sort

  [ -d "$AUDIT_DIR" ] || die "audit dir not found: $AUDIT_DIR"

  local tmp
  tmp="$(mktemp "${TMPDIR:-/tmp}/audit-checksum.XXXXXX")"
  # shellcheck disable=SC2064
  trap "rm -f '$tmp'" EXIT

  # Gather all .jsonl files (including archive/ subdirectory), sorted for
  # deterministic output. Skip the checksum file itself.
  local -a files=()
  while IFS= read -r -d '' f; do
    files+=("$f")
  done < <(find "$AUDIT_DIR" -type f -name '*.jsonl' -not -name 'checksums.sha256' -print0 2>/dev/null | sort -z)

  if [ "${#files[@]}" -eq 0 ]; then
    # No audit logs yet — write an empty checksum file with a header
    {
      printf '# OpenHermes audit-log checksums — computed at %s\n' "$(timestamp_iso)"
      printf '# No .jsonl audit logs present at this time.\n'
    } >"$tmp"
  else
    {
      printf '# OpenHermes audit-log checksums — computed at %s\n' "$(timestamp_iso)"
      for f in "${files[@]}"; do
        local rel="${f#"$OPENHERMES_ROOT/"}"
        shasum -a 256 "$f" | awk -v rel="$rel" '{print $1 "  " rel}'
      done
    } >"$tmp"
  fi

  # Tamper detection: if CHECKSUM_FILE exists and CI-mode is on, ensure
  # the new file matches an existing one (or exits 2 on drift).
  if [ -f "$CHECKSUM_FILE" ] && [ "${CHECKSUM_FAIL_ON_DRIFT:-0}" = "1" ]; then
    if ! diff -q "$CHECKSUM_FILE" "$tmp" >/dev/null 2>&1; then
      printf '[audit-checksum] TAMPER DETECTED — checksums differ from committed\n' >&2
      printf '[audit-checksum] diff:\n' >&2
      diff "$CHECKSUM_FILE" "$tmp" >&2 || true
      exit 2
    fi
  fi

  mv "$tmp" "$CHECKSUM_FILE"
  trap - EXIT
  printf '[audit-checksum] wrote %s (%d audit files hashed)\n' \
    "$CHECKSUM_FILE" "${#files[@]}" >&2

  # Stage for commit if we're in a git tree — actual commit is a separate
  # decision (weekly cron should git-add + git-commit; CI just verifies).
  if git -C "$OPENHERMES_ROOT" rev-parse --show-toplevel >/dev/null 2>&1; then
    git -C "$OPENHERMES_ROOT" add "$CHECKSUM_FILE" 2>&1 | head
  fi

  return 0
}

main "$@"
