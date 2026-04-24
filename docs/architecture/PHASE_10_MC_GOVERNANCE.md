# Phase 10 — Mission Control Governance

> **Status:** ✅ Gate 10 PASSED (config + infrastructure)
> **Date:** 2026-04-24

The original OPENHERMES_HANDOFF plan called for AxonFlow as the governance layer. Per user direction during planning, we pivoted to **Mission Control** as the governance runtime — it's already deployed (runs on `localhost:3100`), already has approval records, and matches our existing workflow. Phase 10 is policy + audit config, not deployment (that's Phase 11).

---

## Artifacts shipped

| File | Purpose |
|---|---|
| `governance/mission-control/policies.yaml` | 4 policy blocks mapping classifier output to MC approval records |
| `governance/audit/README.md` | Audit log format, writer roles, retention policy, what not to log |
| `governance/audit/checksums.sha256` | Initial (empty-state) checksum manifest for tamper evidence |
| `scripts/observability/audit-checksum.sh` | Weekly checksum script, shellcheck-clean, CI-compatible |
| `config/mission-control.yaml` | Board + custom field UUIDs + auth token ref (migrated from OpenClawMaster in Phase 2) |
| `scripts/mc-push.sh` | CLI wrapper: `mc-push {task,approval,comment,list}` (migrated from Phase 5.1 work) |

## Four approval policies

All policies live in `governance/mission-control/policies.yaml` and are consumed by the bridge + `mc-push.sh` during dispatch.

### 1. `publish_requires_mc_approval`

**Trigger:** `governance_class: publish` (from classifier)
**Action:** `require_approval` via Sentinel
**Board:** `approvals`
**Flow:** Elon dispatches a publish_packet to Zuck. Before Zuck executes the actual post, Elon posts an Approval record to MC (`action_type: publish`). Sentinel (board lead) reviews. If approved, Zuck publishes. If rejected, Elon discards the packet and reports to Milo.

### 2. `irreversible_requires_mc_plus_user`

**Trigger:** `governance_class: irreversible`
**Action:** `require_approval_and_halt` — BOTH Sentinel approval AND explicit user chat confirmation required
**Board:** `approvals`
**Flow:** Non-bypassable. Exec/database/secret/financial actions halt entirely until both signals are collected. Either failure aborts.

### 3. `pii_scan_outbound`

**Trigger:** Any outbound tool: `zuck.*`, `milo.send_message`, `milo.send_email`, `hermes.send_*`
**Action:** `scan_and_redact` via `bridge/scripts/sanitize-memory.py`
**Patterns:** email, phone, SSN, credit card, API key, OAuth token
**Flow:** Same sanitizer library as the memory contract. Blocked-severity content is held for user override.

### 4. `budget_enforcement`

**Trigger:** Every handoff envelope
**Action:** `enforce_budget` — `max_tokens`, `max_seconds`, `max_tool_calls`
**Flow:** Sessions exceeding any budget field terminate with `status: failed` and `reason: budget_exceeded_{field}`. Partial work preserved for review; session key logged to audit.

## Per-agent credential attribution

Each agent uses its own bearer token for outbound writes. Audit logs can attribute every external call to the correct agent without ambiguity.

| Agent | Tokens (env-resolved from `~/.openclaw/secrets.json`) |
|---|---|
| Zuck | `ZUCK_TWITTER_TOKEN`, `ZUCK_LINKEDIN_TOKEN` |
| Milo | `MILO_GMAIL_TOKEN`, `MILO_SLACK_TOKEN`, `DISCORD_BOT_TOKEN`, `TELEGRAM_BOT_TOKEN` |
| Cortana | `MISSION_CONTROL_AUTH_TOKEN` (audit writer identity) |

Secret files never in repo. Token references use OpenClaw's `SecretRef` pattern (`source: file, id: /KEY_NAME`) — ciphertext flows through, values stay at rest in `~/.openclaw/secrets.json` (chmod 600).

## Audit sink

`governance/audit/mission-control.jsonl` is the authoritative append-only record. Format: NDJSON, one event per line, rotation weekly.

Write path: any agent that invokes `mc-push.sh approval` or triggers a governed action causes Cortana to append a line to the sink. The sink is **not** tracked in the repo (per public-repo hygiene — PII risk) but the **checksums ARE** tracked for tamper evidence.

## Tamper evidence

`scripts/observability/audit-checksum.sh`:

- Walks `governance/audit/*.jsonl` (including `archive/`)
- Computes SHA-256 per file
- Writes sorted output to `governance/audit/checksums.sha256`
- Stages for commit if inside a git tree
- CI-mode (`CHECKSUM_FAIL_ON_DRIFT=1`) exits 2 on any divergence from the committed checksum

Weekly schedule via OpenClaw cron:

```bash
openclaw cron add \
  --cron "0 0 * * 0" \
  --session isolated \
  --message "bash \$OPENHERMES_ROOT/scripts/observability/audit-checksum.sh" \
  --name "audit-checksum-weekly" \
  --no-deliver
```

Pre-launch run produced the initial empty-state checksum file (0 audit files hashed yet — expected, we haven't dispatched governed actions yet).

## What's NOT in Phase 10

- **MC deployment** — MC runs on `localhost:3100`. Starting it (if stopped) is Phase 11's deployment scope
- **Actual approval roundtrip testing** — Phase 10 is policy + artifacts. End-to-end canary of Milo→Elon→Zuck→MC→Sentinel→approved→publish belongs to Phase 11 when OrbStack compose brings everything up together
- **Ingesting approval-resolved webhooks into Elon's session** — the gateway's dispatch handler needs minor wiring here; deferring to Phase 11
- **Violation alerting** — the contract docs reference Sentinel alerts on memory violations (Phase 9) and policy violations (here). Actual alert path is Phase 12 observability

## Gate 10 Decision

**PASS.** The governance layer is architecturally complete:

- 4 policies encoded in `governance/mission-control/policies.yaml`
- Audit sink format + retention documented
- Per-agent attribution wired via env references
- Tamper-evidence script tested and producing baseline checksums

Runtime validation (approval roundtrip, actual MC write, alert delivery) lands in Phase 11 with the full deployment.

Next: **Phase 11 — OrbStack deployment + launch + verify**.
