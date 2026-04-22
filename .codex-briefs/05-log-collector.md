# Codex Brief #5 — `log-collector.sh`

**Target file:** `$OPENHERMES_ROOT/scripts/observability/log-collector.sh`

**Priority:** Phase 12 (observability before channel migration).

---

## Prompt (paste into Codex)

Produce a bash script (`log-collector.sh`) that tails OrbStack/Docker logs from 3 containers in parallel and emits a unified, structured log stream.

### Requirements

- **Tail these containers concurrently:** `milo`, `elon`, `openhermes_proxy`
- **Prefix each line** with ISO-8601 UTC timestamp and container name: `2026-04-22T20:15:33Z [milo] <line>`
- **JSON merge for structured lines:** if the raw log line begins with `{`, attempt to parse as JSON and merge fields with the wrapper `{ts, container, ...original}`. If parse fails, fall back to plain-text prefix.
- **Emit to stdout** by default.
- **Optional SIEM forwarding:** if `SIEM_ENDPOINT` env var is set, POST each line as NDJSON to that URL with retry (exponential backoff: 1s, 2s, 4s, max 3 retries, then drop the line and log the drop to stderr).
- **Reconnect on container restart:** if `docker logs -f` exits non-zero, wait 2s and re-attach. Don't give up unless the container is permanently gone (check with `docker inspect`).
- **Handle SIGTERM / SIGINT** cleanly: kill background tails, flush any pending SIEM retries, exit 0.

### Implementation notes

- Pure **bash + jq + curl**. No Node, no Python.
- Use background processes (`&`) with `wait` for coordination.
- Use `trap` for signal handling.
- Include a top-of-file comment block with: purpose, required env vars, usage examples, exit codes.

### Example output (no SIEM)

```
2026-04-22T20:15:33Z [milo] {"ts":"2026-04-22T20:15:33Z","container":"milo","level":"info","msg":"session started","session_id":"abc123"}
2026-04-22T20:15:34Z [elon] {"ts":"2026-04-22T20:15:34Z","container":"elon","level":"info","msg":"dispatch","agent":"sagan"}
2026-04-22T20:15:35Z [openhermes_proxy] 192.0.2.1 - - GET /chat/v1 200 12ms
```

(Last line is plain-text because Caddy logs aren't JSON by default; bash prefixes it.)

---

## Acceptance criteria

- Works with `docker compose logs` equivalent commands (OrbStack-compatible)
- Handles a mix of structured (JSON) and unstructured (plain-text) log lines
- `SIEM_ENDPOINT=https://example.com/ingest ./log-collector.sh` forwards, retries, drops on persistent failure
- Script is shellcheck-clean (`shellcheck log-collector.sh` exits 0)
- Runs on macOS (BSD tools) — don't rely on GNU-only flags
