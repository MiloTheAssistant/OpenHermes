# Phase 4 — Nous Hermes Install

> **Status:** ✅ Gate 4 PASSED (2026-04-24)
> **Smoke test result:** `MILO_OK` returned by `minimax-m2.7` via `ollama-cloud` provider
> **Session ID:** `20260424_164106_485794`

---

## Environment

| Item | Value |
|---|---|
| Nous Hermes repo | `/Volumes/BotCentral/Users/milo/repos/hermes-agent/` (sibling to OpenHermes) |
| Pinned tag | `v2026.4.23` (Hermes package version `0.11.0`) |
| Venv | `.venv/` managed by `uv` |
| Hermes home | `~/.hermes/` |
| Config | `~/.hermes/config.yaml` (6.3 KB) |
| Secrets env | `~/.hermes/.env` (chmod 600, outside repo) |
| Logs | `~/.hermes/logs/` |
| Memories | `~/.hermes/memories/MEMORY.md` (57 lines) + `USER.md` (17 lines) |
| Sessions | `~/.hermes/sessions/` |
| SOUL | `~/.hermes/SOUL.md` (default Hermes persona — **preserved for Phase 6 GOTCHA anchor injection**) |

## Default Model (per OpenHermes matrix)

```yaml
model:
  default: ollama/minimax-m2.7:cloud
```

Smoke tests use explicit `--provider ollama-cloud -m minimax-m2.7` for clarity.

## Provider Keys Migrated

Provisioned into `~/.hermes/.env` from `~/.openclaw/secrets.json`:

- `OLLAMA_API_KEY` — Milo primary provider (ollama-cloud)
- `NVIDIA_NIM_API_KEY` — Milo fallback, Neo primary
- `OPENAI_API_KEY` — Codex-adjacent workflows
- `ZAI_API_KEY` — Z.ai tier-3 fallback for Elon, Sentinel/Zuck fallback
- `PERPLEXITY_API_KEY` — Sagan primary
- `OPENROUTER_API_KEY` — Aux LLM for Hermes context compression (resolved a runtime warning during smoke test)
- `XAI_API_KEY` — xAI grok family (optional)

Explicitly cleared per DEC-002 policy:

- `ANTHROPIC_API_KEY=` — blocked for OpenClaw harness use; now blocked at Hermes-provider layer too

## Plan Correction: `hermes claw migrate` EXISTS

**PLAN.md §3.4 (and the original OPENHERMES_HANDOFF plan) claimed `hermes claw migrate` did not exist.** This was based on an earlier WebFetch of `nousresearch/hermes-agent`'s `llms.txt` which listed 7 top-level commands but omitted `claw`. The actual Hermes CLI exposes:

```
hermes claw {migrate, cleanup, clean}
  migrate          Import settings, memories, skills, and API keys from OpenClaw to Hermes
  cleanup / clean  Archive leftover OpenClaw directories after migration
```

Phase 4 therefore used the **native `claw migrate` tool** instead of writing a manual migration script. Outcome was cleaner than the manual path would have been.

### Migration command used

```
hermes claw migrate --preset user-data --yes
```

- `--preset user-data` — excludes secrets (handled separately via controlled `~/.hermes/.env` population)
- `--yes` — non-interactive confirmation

### Migration result (15 migrated, 1 conflict, 20 skipped)

**Migrated:**
- `memory` → `~/.hermes/memories/MEMORY.md`
- `user-profile` → `~/.hermes/memories/USER.md`
- `discord-settings` → `~/.hermes/.env` (non-secret channel settings only)
- `model-config` → `~/.hermes/config.yaml`
- `daily-memory` → appended to `MEMORY.md`
- 2 MCP servers: `context7`, `gmail-milo` → `config.yaml mcp_servers.*`
- `agent-config` → `config.yaml agent/compression/terminal` blocks
- 5 `full-providers` → `config.yaml custom_providers[]`: `ollama`, `zai`, `nim`, `perplexity`, `openai-codex`
- 2 skills → `~/.hermes/skills/openclaw-imports/`: `2brain`, `shopify-admin-api`
- 1 skill-category → `DESCRIPTION.md`

**Conflicts (correctly skipped — preserves Phase 6 clean-slate):**
- `soul` — target `~/.hermes/SOUL.md` exists; default Nous Hermes persona preserved for Phase 6 GOTCHA anchor injection

**Skipped (not applicable to our setup):**
- workspace-agents, messaging-settings (non-Discord), slack-settings, whatsapp-settings, signal-settings, secret-settings (intentional), provider-keys (intentional), tts-config, command-allowlist, shared-skills, tts-assets, raw-config-skip, sensitive-skip (×3), browser-config, approvals-config, memory-backend, skills-config, ui-identity

Full migration report at `~/.hermes/migration/openclaw/20260424T163816`.

## Stale Reference Fixed

`config.yaml model.default` was set by the migration to `openai-codex/gpt-5.4` (the OpenClaw setting at migration time). Manually bumped to `ollama/minimax-m2.7:cloud` per OpenHermes matrix (Milo runs on minimax-m2.7, not gpt-5.5 — gpt-5.5 is Elon's model).

## What Phase 6 Still Needs to Do

With `claw migrate` now handling configuration + memory ingest, Phase 6's scope narrows to:

1. **GOTCHA anchor injection** into `~/.hermes/SOUL.md` (the 8 anchors from PLAN.md §4) while preserving the Nous Hermes default persona that's currently there
2. **Verify `USER.md`** matches our expectations (John-context continuity)
3. **Verify `MEMORY.md`** is free of OpenClaw-Milo-orchestrator baggage (e.g., "I dispatch to specialists") since New Milo delegates to Elon, not directly to specialists
4. **Test that new Milo correctly delegates** to Elon instead of attempting dispatch itself

Phase 6's original scope ("hand-write Nous Hermes equivalents") is no longer needed — it becomes "audit + refine what claw migrate produced".

## Gate 4 Decision

**PASS.** Nous Hermes Agent runs cleanly, smoke test returned expected output via the correct provider/model combination, and Phase 5.1 runtime continues uninterrupted (OpenClaw gateway + 8 agents still active on 2026.4.23).

Next: **Phase 5 — Milo → Elon rename + OAuth proxy + GPT-5.5 on Codex.**
