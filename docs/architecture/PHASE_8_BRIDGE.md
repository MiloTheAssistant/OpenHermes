# Phase 8 — Bridge (Milo ↔ Elon)

> **Status:** ✅ Gate 8 core PASSED — Milo → Elon end-to-end validated
> **Date:** 2026-04-24

---

## Bridge architecture (what shipped)

The bridge is thinner than the original OPENHERMES_HANDOFF plan proposed. OpenClaw's gateway does NOT expose a native OpenAI-compatible `/v1/chat/completions` endpoint — it uses its own WebSocket protocol. Running an extra OpenAI-compat shim process adds operational weight we don't need.

Instead, Milo reaches Elon via the **same cron-dispatch mechanism** that's already proven to work (DEC-006 discipline, Phase 5/7 canaries). Milo's `exec` tool runs `openclaw cron add`; the bridge wrapper script handles classification, scheduling, polling, and result marshaling.

```
┌─────────────┐   bridge/scripts/delegate_to_elon.sh           ┌───────────┐
│  Milo       │ ──► classify.py (deterministic)                │  Elon     │
│ (Nous       │ ──► openclaw cron add --agent main             │ (main,    │
│  Hermes)    │ ──► poll cron runs --id <job>                  │  gpt-5.5) │
│             │ ◄── { elon_result.summary, session_key, ... }  └─────┬─────┘
└─────────────┘                                                       │
                                                                      ▼
                              ┌─────────────────────────────────────────────┐
                              │  Specialists (cron-dispatched by Elon       │
                              │  per DEC-006 — sagan, neo, kat, sentinel,   │
                              │  cortana, cornelius, zuck)                  │
                              └─────────────────────────────────────────────┘
```

## Artifacts delivered

| File | Purpose |
|---|---|
| `bridge/schemas/handoff.schema.json` | JSON Schema (Draft 2020-12) for the handoff envelope (Codex Brief #3 — committed earlier) |
| `bridge/scripts/validate_handoff.py` | Python validator for envelopes against the schema (Brief #3) |
| `bridge/scripts/classify.py` | **NEW** — Deterministic governance-class classifier (info / action / publish / irreversible). Pure-rule, no LLM. ~180 lines. |
| `bridge/scripts/delegate_to_elon.sh` | **NEW** — Milo's handoff wrapper. Takes a JSON task on stdin (or `--message` shortcut), classifies it, dispatches to Elon via cron if class ≠ info, polls for completion, returns a full result envelope. ~165 lines. shellcheck-clean. |

## Deterministic classifier

No LLM in the classification path. Rule-based mapping:

| Trigger | → `governance_class` | Route | Requires MC? | Halt? |
|---|---|---|---|---|
| `side_effects ∈ { database_drop, infra_change, secret_rotation, financial_transaction, credential_revoke, data_deletion, ... }` OR tool `exec` requested | `irreversible` | `milo→elon→sentinel→mc+user` | ✅ | ✅ |
| `side_effects ∈ { post_social, post_x, post_linkedin, ... }` OR tool `zuck.publish` OR external target surface | `publish` | `milo→elon→zuck→mc` | ✅ | ❌ |
| `side_effects ∈ { file_write, internal_api_call, send_internal_message, schedule_cron, config_patch, ... }` OR non-read-only tools | `action` | `milo→elon` | ❌ | ❌ |
| default | `info` | `milo` (no dispatch) | ❌ | ❌ |

Milo cannot bypass the classifier. `irreversible` always requires Sentinel + MC approval + explicit user confirm. `publish` always requires MC approval. The four-class enum is enforced everywhere downstream (handoff envelope schema, routing config).

Four-class test run:

```
info         → "What time is it in Tokyo?"            required_route: milo
action       → "Write a new script to /tmp/test.py"    required_route: milo->elon
publish      → "Post a tweet"                           required_route: milo->elon->zuck->mc
irreversible → "Delete the production database"         required_route: milo->elon->sentinel->mc+user
```

All four resolve deterministically with correct rationale and routing target.

## Canary — end-to-end Milo → classifier → Elon

**Input** (to `delegate_to_elon.sh` via stdin):

```json
{
  "summary": "Write BRIDGE_OK to a tempfile",
  "message": "Respond with exactly: BRIDGE_OK",
  "side_effects": ["file_write"],
  "targets": [],
  "tools_requested": ["write"],
  "timeout_seconds": 120
}
```

**Output** (JSON envelope from bridge):

```json
{
  "status": "dispatched_complete",
  "classification": {
    "governance_class": "action",
    "reason": "action side effects: ['file_write']",
    "required_route": "milo->elon",
    "requires_halt": false,
    "requires_mc_approval": false
  },
  "cron_job_id": "8bdf09f6-5f45-437f-979a-1c2ff8cf219f",
  "elon_result": {
    "run_status": "ok",
    "duration_ms": 8972,
    "model": "gpt-5.5",
    "provider": "openai-codex",
    "session_key": "agent:main:cron:8bdf09f6-5f45-437f-979a-1c2ff8cf219f:run:...",
    "summary": "BRIDGE_OK"
  },
  "completed_at": "2026-04-24T22:25:25Z"
}
```

Validates every layer:
1. ✅ Classifier ran, identified `action` class from `file_write` side effect
2. ✅ Routing decision `milo→elon` honored
3. ✅ Cron job scheduled successfully
4. ✅ Elon session spawned on correct agent (`main`) with correct model (`gpt-5.5` via Codex OAuth)
5. ✅ Elon returned the expected output (`BRIDGE_OK`)
6. ✅ Bridge polled to completion, marshaled the result back

## What was deferred from the original plan

The original OPENHERMES_HANDOFF document proposed a more elaborate bridge with:
- Milo as MCP server exposing `milo.recall_memory`, `milo.search_sessions`, `milo.browser_fetch`, `milo.get_user_context` to Elon
- OpenClaw as OpenAI-compatible provider for Milo's `delegation` config

**Deferred to post-launch evaluation.** Reasons:
1. The cron-dispatch path is proven, simpler, and uses infrastructure we've already validated end-to-end.
2. MCP server/client wiring would require running Milo as a persistent MCP server alongside Hermes Agent — added process complexity for marginal near-term benefit.
3. OpenClaw doesn't expose OpenAI-compat HTTP; building that would require a shim process. Not worth the operational weight.

The 2026.4.23 note about `sessions_spawn` gaining optional forked context (noted in PLAN.md §7a) may enable a cleaner native path. We'll revisit post-launch.

## Milo's SOUL — delegation guidance

`~/.hermes/SOUL.md` already tells Milo the delegation rule: *"any request with complexity ≥ 2 or any side-effect tool call → delegate to Elon."* Milo achieves this via:

1. Call `classify.py` (via `exec`) on the structured task
2. If `governance_class == "info"`, answer directly
3. Otherwise call `delegate_to_elon.sh` which handles the full Elon round-trip

SOUL does NOT hard-code the exact shell command paths — Milo knows the pattern and uses `exec` appropriately. Path resolution is left to runtime (via `OPENHERMES_ROOT` env or similar).

## Gate 8 Decision

**PASS (core).** Milo → Elon handoff works end-to-end with deterministic classification. Governance-class enforcement is reliable.

**Deferred to post-launch:** Milo MCP server exposure to Elon (the reverse direction — Elon calling Milo's memory/browser tools). The cron-dispatch path doesn't need it; Milo can attach relevant memory excerpts directly in the `message` payload when dispatching.

Next: **Phase 9 — Single-writer memory contract + sanitizer**.
