#!/usr/bin/env bash
# Usage:
#   export OPENCLAW_MASTER=/path/to/OpenClawMaster
#   export OPENHERMES_ROOT=/path/to/OpenHermes
#   ./move-from-openclawmaster.sh scripts/migration/manifest.txt
#
# Manifest format (whitespace-separated):
#   SOURCE_PATH  TARGET_PATH
#   # comment
#
# Example manifest lines:
#   AGENTS.md                           docs/architecture/AGENTS.md
#   agents/Sagan.md                     agents/specialists/sagan/IDENTITY.md
#   state/Decision_Log.md               state/Decision_Log.md
#   tools/scripts/mc-push.sh            scripts/mc-push.sh

set -euo pipefail

FORCE_OVERWRITE=0
MOVED_COUNT=0
SKIPPED_COUNT=0
WARNING_COUNT=0
FINDINGS_COUNT=0
SCAN_INTERVAL=10
MOVED_SINCE_SCAN=0

timestamp() {
  date -u +"%Y-%m-%dT%H:%M:%SZ"
}

log() {
  local level="$1"
  shift
  printf '[%s] %s: %s\n' "$(timestamp)" "$level" "$*" >&2
}

die() {
  log ERROR "$*"
  exit 1
}

usage() {
  cat >&2 <<'EOF'
Usage:
  export OPENCLAW_MASTER=/path/to/OpenClawMaster
  export OPENHERMES_ROOT=/path/to/OpenHermes
  ./move-from-openclawmaster.sh [--force] path/to/manifest.txt

Options:
  --force    Overwrite conflicting targets without prompting.
  --help     Show this message.
EOF
}

require_env_path() {
  local name="$1"
  local value="${!name:-}"

  [ -n "$value" ] || die "missing required environment variable: $name"
  case "$value" in
    /*) ;;
    *) die "$name must be an absolute path: $value" ;;
  esac
  [ -d "$value" ] || die "$name is not a directory: $value"
}

ensure_git_repo() {
  local repo_root="$1"
  git -C "$repo_root" rev-parse --show-toplevel >/dev/null 2>&1 || die "not a git working tree: $repo_root"
}

append_unique_line() {
  local file_path="$1"
  local line="$2"

  mkdir -p "$(dirname "$file_path")"
  touch "$file_path"
  if ! grep -Fqx -- "$line" "$file_path" 2>/dev/null; then
    printf '%s\n' "$line" >>"$file_path"
  fi
}

append_log_entry() {
  local source_rel="$1"
  local target_rel="$2"
  local entry_suffix=" $source_rel -> $target_rel"

  touch "$MIGRATION_LOG"
  if ! grep -Fq -- "$entry_suffix" "$MIGRATION_LOG" 2>/dev/null; then
    printf '%s%s\n' "$(timestamp)" "$entry_suffix" >>"$MIGRATION_LOG"
  fi
}

fallback_scan() {
  local output_file
  output_file="$(mktemp "${TMPDIR:-/tmp}/openhermes-grep-scan.XXXXXX")"
  local pattern='(BEGIN [A-Z0-9 ]*PRIVATE KEY|AKIA[0-9A-Z]{16}|api[_-]?key|token|secret|service-account)'

  if grep -RInE --exclude-dir=.git --exclude-dir=.venv --exclude='migration-log.txt' --exclude='migrated-source-files.txt' "$pattern" "$OPENHERMES_ROOT" >"$output_file" 2>/dev/null; then
    FINDINGS_COUNT=$((FINDINGS_COUNT + 1))
    cat "$output_file" >&2
    rm -f "$output_file"
    print_summary >&2
    exit 1
  fi

  rm -f "$output_file"
}

run_scan() {
  local output_file
  output_file="$(mktemp "${TMPDIR:-/tmp}/openhermes-gitleaks.XXXXXX")"

  log INFO "running batched secret scan"
  if command -v gitleaks >/dev/null 2>&1; then
    if ! gitleaks detect --source "$OPENHERMES_ROOT" --no-git --redact >"$output_file" 2>&1; then
      FINDINGS_COUNT=$((FINDINGS_COUNT + 1))
      cat "$output_file" >&2
      rm -f "$output_file"
      print_summary >&2
      exit 1
    fi
  else
    fallback_scan
  fi

  rm -f "$output_file"
}

restore_target() {
  local target_abs="$1"
  local backup_abs="$2"
  local existed_before="$3"

  if [ "$existed_before" -eq 1 ]; then
    cp -p "$backup_abs" "$target_abs"
  else
    rm -f "$target_abs"
  fi
}

prompt_conflict_action() {
  local target_rel="$1"

  if [ "$FORCE_OVERWRITE" -eq 1 ]; then
    printf 'overwrite\n'
    return
  fi

  if [ ! -r /dev/tty ] || [ ! -w /dev/tty ]; then
    die "content conflict for $target_rel and no interactive terminal available; rerun with --force to overwrite"
  fi

  while true; do
    printf 'Conflict for %s: overwrite, skip, or abort? [o/s/a]: ' "$target_rel" >/dev/tty
    IFS= read -r reply </dev/tty || die "failed to read operator response"
    case "$reply" in
      o|O|overwrite|OVERWRITE)
        printf 'overwrite\n'
        return
        ;;
      s|S|skip|SKIP)
        printf 'skip\n'
        return
        ;;
      a|A|abort|ABORT)
        printf 'abort\n'
        return
        ;;
      *)
        log WARN "invalid response for conflict on $target_rel: $reply"
        ;;
    esac
  done
}

process_manifest_entry() {
  local source_rel="$1"
  local target_rel="$2"
  local source_abs="$OPENCLAW_MASTER/$source_rel"
  local target_abs="$OPENHERMES_ROOT/$target_rel"
  local target_dir backup_abs existed_before action

  if [ ! -e "$source_abs" ]; then
    WARNING_COUNT=$((WARNING_COUNT + 1))
    log WARN "source missing, skipping: $source_rel"
    return
  fi

  if [ -d "$source_abs" ]; then
    die "manifest entry points to a directory, expected a file: $source_rel"
  fi

  target_dir="$(dirname "$target_abs")"
  mkdir -p "$target_dir"

  if [ -e "$target_abs" ]; then
    if cmp -s "$source_abs" "$target_abs"; then
      SKIPPED_COUNT=$((SKIPPED_COUNT + 1))
      append_unique_line "$MIGRATED_SOURCES" "$source_rel"
      return
    fi

    action="$(prompt_conflict_action "$target_rel")"
    case "$action" in
      overwrite) ;;
      skip)
        SKIPPED_COUNT=$((SKIPPED_COUNT + 1))
        log INFO "skipping conflicting target: $target_rel"
        return
        ;;
      abort)
        die "operator aborted on conflict: $target_rel"
        ;;
      *)
        die "unexpected conflict action: $action"
        ;;
    esac
  fi

  existed_before=0
  if [ -e "$target_abs" ]; then
    existed_before=1
  fi

  backup_abs="$(mktemp "${TMPDIR:-/tmp}/openhermes-target-backup.XXXXXX")"
  if [ "$existed_before" -eq 1 ]; then
    cp -p "$target_abs" "$backup_abs"
  fi

  cp -p "$source_abs" "$target_abs"

  if ! git -C "$OPENHERMES_ROOT" add -- "$target_rel"; then
    restore_target "$target_abs" "$backup_abs" "$existed_before"
    rm -f "$backup_abs"
    die "git add failed for $target_rel"
  fi

  rm -f "$backup_abs"
  append_log_entry "$source_rel" "$target_rel"
  append_unique_line "$MIGRATED_SOURCES" "$source_rel"

  MOVED_COUNT=$((MOVED_COUNT + 1))
  MOVED_SINCE_SCAN=$((MOVED_SINCE_SCAN + 1))
  log INFO "migrated $source_rel -> $target_rel"

  if [ "$MOVED_SINCE_SCAN" -ge "$SCAN_INTERVAL" ]; then
    run_scan
    MOVED_SINCE_SCAN=0
  fi
}

print_summary() {
  printf '[%s] INFO: summary: %s moved, %s skipped, %s warnings, %s findings\n' \
    "$(timestamp)" "$MOVED_COUNT" "$SKIPPED_COUNT" "$WARNING_COUNT" "$FINDINGS_COUNT"
}

on_exit() {
  local rc="$1"

  if [ "$rc" -ne 0 ]; then
    log ERROR "script aborted with exit code $rc"
  fi
}

trap 'on_exit "$?"' EXIT

while [ "$#" -gt 0 ]; do
  case "$1" in
    --force)
      FORCE_OVERWRITE=1
      shift
      ;;
    --help|-h)
      usage
      exit 0
      ;;
    --*)
      usage
      die "unknown option: $1"
      ;;
    *)
      break
      ;;
  esac
done

[ "$#" -eq 1 ] || {
  usage
  die "expected exactly one manifest file argument"
}

MANIFEST_PATH="$1"
[ -f "$MANIFEST_PATH" ] || die "manifest file not found: $MANIFEST_PATH"

require_env_path OPENCLAW_MASTER
require_env_path OPENHERMES_ROOT
ensure_git_repo "$OPENHERMES_ROOT"

MIGRATION_DIR="$OPENHERMES_ROOT/scripts/migration"
MIGRATION_LOG="$MIGRATION_DIR/migration-log.txt"
MIGRATED_SOURCES="$MIGRATION_DIR/migrated-source-files.txt"

mkdir -p "$MIGRATION_DIR"
touch "$MIGRATION_LOG" "$MIGRATED_SOURCES"

line_number=0
while IFS= read -r manifest_line || [ -n "$manifest_line" ]; do
  line_number=$((line_number + 1))
  trimmed_line="${manifest_line#"${manifest_line%%[![:space:]]*}"}"

  [ -n "$trimmed_line" ] || continue
  case "$trimmed_line" in
    \#*) continue ;;
  esac

  IFS=' ' read -r source_rel target_rel extra_field <<<"$trimmed_line"
  [ -n "${source_rel:-}" ] || die "missing source path on line $line_number: $manifest_line"
  [ -n "${target_rel:-}" ] || die "missing target path on line $line_number: $manifest_line"
  [ -z "${extra_field:-}" ] || die "invalid manifest format on line $line_number: $manifest_line"

  case "$source_rel" in
    /*) die "source path must be relative on line $line_number: $source_rel" ;;
  esac
  case "$target_rel" in
    /*) die "target path must be relative on line $line_number: $target_rel" ;;
  esac

  process_manifest_entry "$source_rel" "$target_rel"
done <"$MANIFEST_PATH"

if [ "$MOVED_SINCE_SCAN" -gt 0 ]; then
  run_scan
fi

print_summary >&2
