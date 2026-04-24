# Audit Log Directory

Append-only audit sinks for OpenHermes governance events. **Do not rewrite or delete entries.** Rotation is weekly; old logs archive but stay recoverable.

## Files

| File | Writer | Events |
|---|---|---|
| `mission-control.jsonl` | Cortana (via `mc-push.sh` approval flow) | Every MC approval decision, policy trigger, budget violation |
| `memory-writes.jsonl` | Nous Hermes Milo | Every successful `MEMORY.md` / `USER.md` write with timestamp, writer process, file range, content description, git SHA |
| `memory-violations.jsonl` | Sentinel (alerting layer) | Failed write attempts by non-Milo processes against memory files |
| `incidents/` | Milo (manual filing) | Post-incident reports: secret exposures, policy violations, rollbacks. One directory per incident, timestamped |

All `.jsonl` files are treated as immutable. The pre-commit hook rejects changes to existing lines; only appends are permitted.

## Format

Each line is a single JSON object with at minimum:

```json
{
  "ts": "2026-04-24T22:30:00Z",
  "event": "approval_resolved | policy_trigger | budget_violation | memory_write | memory_violation",
  "writer": "milo | cortana | sentinel",
  "payload": { ... event-specific ... }
}
```

## Tamper evidence

`scripts/observability/audit-checksum.sh` computes a SHA-256 over every `.jsonl` file in this directory and writes the results to `checksums.sha256`. Committed weekly. A checksum diff without a corresponding audit-line append flags a rewrite — caught on PR review or by the weekly CI job.

## Retention

Rolling retention with archive:

- Active window: 90 days in the live `.jsonl` file
- Archive: older entries compressed to `archive/YYYY-WW.jsonl.gz`
- Forever-preserved: `checksums.sha256` history in git

## What NOT to log

- Raw secrets or token values (audit events reference `secret_ref: "/KEY_NAME"` instead)
- User PII beyond what's necessary to identify an affected session
- Full message bodies from external channels (log `message_hash` only)
- Large file contents (log `content_bytes`, `content_sha256`)

Writer processes are responsible for not leaking sensitive payloads into the audit sink. The sanitizer does NOT cover audit payload redaction — that's the caller's responsibility.
