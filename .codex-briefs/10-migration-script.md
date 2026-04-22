# Codex Brief #10 — Migration script `move-from-openclawmaster.sh`

**Target file:** `$OPENHERMES_ROOT/scripts/migration/move-from-openclawmaster.sh`

**Priority:** Blocks Phase 2 (content migration).

---

## Prompt (paste into Codex)

Produce a bash script (`move-from-openclawmaster.sh`) that moves files from the `OpenClawMaster` repo into the new `OpenHermes` repo, preserving git history logically (via `git mv` within the destination repo), with sanitization guardrails and idempotency.

### Inputs

- **Env vars (REQUIRED — fail fast if missing):**
  - `OPENCLAW_MASTER` — absolute path to OpenClawMaster working tree
  - `OPENHERMES_ROOT` — absolute path to OpenHermes working tree

- **Positional arg:** path to a manifest file with lines of format:
  ```
  SOURCE_REL_PATH  TARGET_REL_PATH
  ```
  where `SOURCE_REL_PATH` is relative to `OPENCLAW_MASTER` and `TARGET_REL_PATH` is relative to `OPENHERMES_ROOT`. Lines starting with `#` are comments. Blank lines ignored.

### Behavior

For each manifest entry:

1. **Verify source exists** in `OPENCLAW_MASTER`. If not, log a warning to stderr and continue (allow manifests that reference optional files).
2. **Verify target parent directory exists** in `OPENHERMES_ROOT`. `mkdir -p` as needed.
3. **Copy** the file from `OPENCLAW_MASTER/SOURCE_REL_PATH` to `OPENHERMES_ROOT/TARGET_REL_PATH`. Preserve mode.
4. **`git add`** the new file inside `OPENHERMES_ROOT`.
5. **Append to a manifest-scoped migration log** at `OPENHERMES_ROOT/scripts/migration/migration-log.txt` with format: `<ISO-timestamp> <SOURCE> -> <TARGET>`.
6. Track a running list of files in `OPENCLAW_MASTER` that were migrated (for the cleanup phase later — do NOT delete from OpenClawMaster in this script; defer until post-launch).

### Batched scanning

After every 10 files moved, run `gitleaks detect --source $OPENHERMES_ROOT --no-git --redact` (or a best-available equivalent if gitleaks is missing — at minimum, grep for common key patterns). If any findings, halt the script, print the findings, exit 1.

### Idempotency

- Re-running the script with the same manifest must not produce duplicate log entries or duplicate file content.
- If target file already exists and content matches source, skip silently.
- If target file already exists and content DIFFERS, prompt the operator: overwrite, skip, or abort.

### Failure modes

- Missing env var → exit 1 with clear error
- Missing manifest file → exit 1
- Gitleaks finding → exit 1 with redacted output
- Source file missing → warn, continue
- Git operation fails → abort, leave working tree in the state before the failed op
- `set -euo pipefail` at the top; explicit error traps

### Logging

- All operations to stderr in format: `[YYYY-MM-DDTHH:MM:SSZ] <level>: <message>`
- Success line per file
- Summary at end: X moved, Y skipped (already present), Z warnings, W findings

### Usage comment at top

```
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
```

### Pure bash

No Python, no Node. `bash`, `git`, `gitleaks` (optional fallback), `grep`, `awk`.

---

## Acceptance criteria

- `shellcheck move-from-openclawmaster.sh` exits 0
- Script handles a 3-line test manifest correctly (one existing, one missing optional, one already-present)
- Running twice produces no duplicate log entries
- Gitleaks finding triggers an abort with exit 1
- Operator prompt appears on content conflict (unless `--force` or similar flag to auto-overwrite is added — if so, document it)
- Works on macOS (BSD tools) — don't rely on GNU-only features
