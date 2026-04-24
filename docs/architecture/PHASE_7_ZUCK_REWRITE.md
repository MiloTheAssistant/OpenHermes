# Phase 7 — Zuck Rewrite (Mark Zuckerberg Social Maven)

> **Status:** ✅ Gate 7 PASSED
> **Date:** 2026-04-24

## Persona Rewrite

`agents/Zuck.md` fully replaced. Removed:
- Email triage responsibilities (now Milo's, per Phase 6 scope)
- "Email Triage, Drafting & Communication Intelligence" description
- Email-oriented deliverable envelope

Added:
- Mark Zuckerberg archetype — confident without bombast, platform-literate, conversion-aware
- Social publisher scope only (X, LinkedIn, Threads, Instagram, blog)
- Explicit memory firewall — zero access to Milo's memory stores
- `ZUCK_ENVELOPE` deliverable structure per-platform with `post_id`, `url`, `approved_by_mc`
- "What Zuck Is Not" section explicitly denying content-writing, research, orchestration, inbox scope

Preserves: restrictions from original Hermes persona (no forward/CC/BCC, no impersonation, X manual-only per DEC-004, config/channels.yaml-gated posting).

## Runtime Rename: `id: hermes` → `id: zuck`

Executed cleanly in one gateway-restart cycle:

| Item | Before | After |
|---|---|---|
| `openclaw.json` agent list entry | `id: hermes, name: Hermes, model: ollama/glm-5.1:cloud` | `id: zuck, name: Zuck, model: ollama/glm-5.1:cloud` |
| Workspace path | `~/.openclaw/workspace-hermes/` | `~/.openclaw/workspace-zuck/` |
| Agents folder | `~/.openclaw/agents/hermes/` | `~/.openclaw/agents/zuck/` |
| Memory DB | `~/.openclaw/memory/hermes.sqlite` | `~/.openclaw/memory/zuck.sqlite` |
| Session-key prefix | `agent:hermes:*` | `agent:zuck:*` |
| `tools.allow` | `[read, write, memory_search, memory_get]` | `[read, write]` — memory firewall enforced |

No cron jobs referenced `hermes` (checked pre-rename), so no follow-on migrations needed.

## Memory Firewall Enforcement

Zuck's `tools.allow` in `openclaw.json` now reads:

```json
"tools": {
  "allow": ["read", "write"]
}
```

`memory_search` and `memory_get` are removed. Zuck cannot read `MEMORY.md`/`USER.md` even if he tries. Per `agents/Zuck.md`, contextual input comes only from `publish_packet` sent by Elon.

## Smoke Test

**Cron dispatch to `agent:zuck`:**

```
openclaw cron add --agent zuck --session isolated \
  --message "Respond with exactly: ZUCK_PUBLISHER_OK" \
  --name "phase7-zuck-smoke" --no-deliver --delete-after-run
```

**Result:**

| Field | Value |
|---|---|
| `status` | `ok` |
| `duration` | 40,213 ms (Ollama Pro slot cold warm-up; expected on first call after restart) |
| `model` | `glm-5.1:cloud` |
| `provider` | `ollama` |
| `sessionKey` | `agent:zuck:cron:a2442fec-...` ← the renamed ID is honored end-to-end |
| `summary` | `ZUCK_PUBLISHER_OK` |

Dispatch worked, model is correct, session-key prefix shows the rename took effect.

## Updated Agent Roster (post-Phase-7)

Live via `openclaw gateway call health`:

| agentId | name | Runtime status |
|---|---|---|
| `main` | Elon | OK (gpt-5.5) |
| `zuck` | Zuck | OK (glm-5.1:cloud) — **NEW** |
| `sagan` | Sagan | OK |
| `neo` | Neo | OK |
| `kat` | Kat | OK |
| `sentinel` | Sentinel | OK |
| `cortana` | Cortana | OK |
| `cornelius` | Cornelius | OK |

8 agents. No Hermes anywhere.

## Gate 7 Decision

**PASS.** Zuck persona matches the Mark Zuckerberg maven archetype, runtime rename clean, memory firewall enforced at the tool-allowlist layer, smoke test returns correct output on the correct session-key prefix.

Next: **Phase 8 — Bridge classifier + bidirectional MCP wiring (Milo ↔ Elon)**.
