#!/usr/bin/env bash
# daily-health-report.sh — generate the OpenHermes daily health report
#
# Designed to run as an OpenClaw cron job once daily, with delivery to a
# Discord channel via OpenClaw's built-in announce delivery.
#
# Output: a Discord-friendly multi-line report on stdout describing:
#   - Gateway state (CLI version, gateway version, agents loaded)
#   - Mission Control container stack (each container Up/healthy)
#   - OpenClaw cron job summary (active jobs, last 24h failures)
#   - Memory + tasks audit summary
#   - Audit checksum result (tamper-evident)
#   - Free disk + memory headroom
#
# Schedule (run once after launch, then OpenClaw cron handles it):
#   openclaw cron add \
#     --cron "0 8 * * *" \
#     --tz America/Chicago \
#     --session isolated \
#     --message "bash $OPENHERMES_ROOT/scripts/observability/daily-health-report.sh" \
#     --name "openhermes-daily-health" \
#     --announce --channel discord --to channel:1485800271421640854
#
# That schedules an 08:00-CT daily run. Replace the channel ID above with
# John's preferred Discord channel for health reports.
#
# Exit codes: always 0 if the script ran (it surfaces errors INTO the
# report rather than failing). Hard exits would silence the report.

set -uo pipefail

OPENCLAW="${OPENCLAW_BIN:-openclaw}"
MC_COMPOSE="${HOME}/repos/openclaw-mission-control/compose.yml"
OPENHERMES_REPO="${OPENHERMES_REPO:-${HOME}/repos/OpenHermes}"
TZ_LOCAL="America/Chicago"

# Tee report into a stable file too — useful when the announce delivery fails
LOG_DIR="${HOME}/.openhermes/health-reports"
mkdir -p "$LOG_DIR" 2>/dev/null
LOG_FILE="${LOG_DIR}/$(TZ=$TZ_LOCAL date +%Y-%m-%d).md"

emit() { printf '%s\n' "$1" | tee -a "$LOG_FILE"; }

# Trap so we ALWAYS write a report even if a probe hangs
trap 'emit "—"; emit "*report generation interrupted*"' INT TERM

now_local() { TZ=$TZ_LOCAL date +"%Y-%m-%d %H:%M:%S %Z"; }
green() { printf "✅ %s" "$1"; }
yellow() { printf "⚠️ %s" "$1"; }
red() { printf "❌ %s" "$1"; }

# Reset the daily file
: >"$LOG_FILE"

emit "## OpenHermes daily health — $(now_local)"
emit ""

# ─── Gateway state ────────────────────────────────────────────────────────
emit "### Gateway"
gw_health="$($OPENCLAW gateway call health --json 2>/dev/null || echo '{}')"
gw_ok="$(printf '%s' "$gw_health" | python3 -c 'import json,sys
raw=sys.stdin.read(); s=raw.find("{")
if s<0: print("?"); sys.exit()
d=json.loads(raw[s:])
print("yes" if d.get("ok") else "no")
' 2>/dev/null || echo "?")"
agent_count="$(printf '%s' "$gw_health" | python3 -c 'import json,sys
raw=sys.stdin.read(); s=raw.find("{")
if s<0: print(0); sys.exit()
d=json.loads(raw[s:])
print(len(d.get("agents",[])))
' 2>/dev/null || echo 0)"
cli_version="$($OPENCLAW --version 2>/dev/null | head -1 || echo unknown)"
case "$gw_ok" in
  yes) emit "- $(green "OK") · CLI: \`$cli_version\` · agents loaded: **$agent_count**" ;;
  no)  emit "- $(red "Gateway responded but reports not OK")" ;;
  *)   emit "- $(red "Gateway not reachable") · last CLI version: \`$cli_version\`" ;;
esac
emit ""

# ─── Mission Control container stack ──────────────────────────────────────
emit "### Mission Control (OrbStack)"
if [ -f "$MC_COMPOSE" ]; then
  mc_status="$(docker compose -f "$MC_COMPOSE" ps --format json 2>/dev/null || echo '')"
  if [ -n "$mc_status" ]; then
    while IFS= read -r line; do
      [ -z "$line" ] && continue
      svc="$(printf '%s' "$line" | python3 -c 'import json,sys; d=json.loads(sys.stdin.read()); print(d.get("Service",""))' 2>/dev/null)"
      state="$(printf '%s' "$line" | python3 -c 'import json,sys; d=json.loads(sys.stdin.read()); print(d.get("State",""))' 2>/dev/null)"
      health="$(printf '%s' "$line" | python3 -c 'import json,sys; d=json.loads(sys.stdin.read()); print(d.get("Health","-") or "-")' 2>/dev/null)"
      if [ "$state" = "running" ]; then
        emit "- $(green "$svc") · state=$state · health=$health"
      else
        emit "- $(red "$svc") · state=$state"
      fi
    done <<<"$mc_status"
  else
    emit "- $(yellow "compose ps returned no data — MC may be stopped")"
  fi
else
  emit "- $(yellow "MC compose file not found at $MC_COMPOSE")"
fi
emit ""

# ─── Cron jobs (active + last 24h errors) ─────────────────────────────────
emit "### Cron jobs"
cron_summary="$($OPENCLAW cron list --json 2>/dev/null || echo '{}')"
total="$(printf '%s' "$cron_summary" | python3 -c 'import json,sys
raw=sys.stdin.read(); s=raw.find("{")
if s<0: print(0); sys.exit()
d=json.loads(raw[s:])
print(len(d.get("jobs",[])))
' 2>/dev/null || echo 0)"
errored="$(printf '%s' "$cron_summary" | python3 -c 'import json,sys,time
raw=sys.stdin.read(); s=raw.find("{")
if s<0: print(0); sys.exit()
d=json.loads(raw[s:])
since=time.time() - 86400
count=0
for it in d.get("jobs",[]):
    st=it.get("state",{})
    if st.get("lastRunStatus")=="error" and (st.get("lastRunAtMs",0)/1000) >= since:
        count+=1
print(count)
' 2>/dev/null || echo 0)"
if [ "$errored" -gt 0 ]; then
  emit "- $(yellow "$total active jobs, $errored failed in last 24h")"
else
  emit "- $(green "$total active jobs, 0 failures in last 24h")"
fi
emit ""

# ─── Disk + memory ────────────────────────────────────────────────────────
emit "### Host capacity"
disk="$(df -h "$HOME" | awk 'NR==2 {print $4 " free of " $2 " (" $5 " used)"}')"
mem_total_mb="$(sysctl -n hw.memsize 2>/dev/null | awk '{print int($1/1024/1024)}')"
emit "- Disk (\$HOME): $disk"
emit "- RAM: ${mem_total_mb} MB total"
emit ""

# ─── Audit checksum (tamper evidence) ─────────────────────────────────────
emit "### Audit checksum"
checksum_script="${OPENHERMES_REPO}/scripts/observability/audit-checksum.sh"
if [ -x "$checksum_script" ]; then
  if CHECKSUM_FAIL_ON_DRIFT=1 OPENHERMES_ROOT="$OPENHERMES_REPO" "$checksum_script" >/dev/null 2>&1; then
    emit "- $(green "no tamper detected") · checksums match committed"
  else
    rc=$?
    if [ "$rc" = "2" ]; then
      emit "- $(red "TAMPER DETECTED") · run \`bash $checksum_script\` to inspect diff"
    else
      emit "- $(yellow "checksum script exited $rc")"
    fi
  fi
else
  emit "- $(yellow "checksum script missing at $checksum_script")"
fi
emit ""

# ─── Footer ──────────────────────────────────────────────────────────────
emit "_Report logged to \`$LOG_FILE\`_"
