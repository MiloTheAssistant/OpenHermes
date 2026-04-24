# Phase 9 — Single-Writer Memory Contract + Sanitizer

> **Status:** ✅ Gate 9 PASSED
> **Date:** 2026-04-24

---

## Contract

`docs/governance/MEMORY_CONTRACT.md` ships as the authoritative document. Rules:

- **Milo is the sole writer** of `~/.hermes/memories/MEMORY.md` and `~/.hermes/memories/USER.md`
- **Cortana writes only** `workspace/memory/TELEMETRY.md` (separate path, separate subsystem)
- **Specialists read memory via `memory_search` / `memory_get`** — those are the only memory tools in their allowlists, and they are read-only by design
- **Zuck is memory-firewalled** — no memory tools at all (enforced at `openclaw.json` `tools.allow` layer; confirmed in Phase 7)
- **Prompt-injection-suspect content** passes through `bridge/scripts/sanitize-memory.py` before any memory write

## Enforcement at the tool-architecture layer

The contract is enforced by what tools exist, not by a pre-commit hook on the repo (the memory files are runtime state, outside the OpenHermes repo). Audit of `tools.allow` per agent:

| Agent | `memory_*` in allowlist | Write tools | Role vs. memory |
|---|---|---|---|
| `main` (Elon) | none | no | Dispatches work; doesn't need to read memory directly |
| `zuck` | **NONE** | yes | **Firewalled** — cannot read memory at all |
| `sagan` | read-only (search, get) | yes | Reads research context, writes research artifacts (not memory) |
| `neo` | read-only (search, get) | yes | Reads engineering context, writes code files (not memory) |
| `kat` | read-only (search, get) | yes | Reads brand-voice + past content, writes drafts (not memory) |
| `sentinel` | read-only (search, get) | no | Reads for QA review only |
| `cortana` | read-only (search, get) | yes | Writes state/telemetry to its own path, not MEMORY.md |
| `cornelius` | none | no | Heavy coding; doesn't touch memory directly |

**No agent has a `memory_write` tool.** OpenClaw doesn't expose one in its tool surface. Memory writes happen through:

1. Nous Hermes Milo, using its built-in memory management (via `hermes memory` CLI or chat-triggered internal writes)
2. OpenClaw's Memory Dreaming cron — runs nightly at 03:00 (isolated agent turn per 2026.4.23 decouple-from-heartbeat fix), promotes short-term recalls into canonical long-term entries

## Sanitizer

`bridge/scripts/sanitize-memory.py` — 180-line pure-rule sanitizer. Detects:

- **Direct instruction overrides** ("ignore previous instructions", "you are now", "forget everything", etc.) → verdict `blocked`
- **Role-hijack markers** (markdown headers `# SYSTEM`, XML `<system>`, brackets `[SYSTEM]`) → verdict `suspicious` alone, `blocked` combined with override
- **Embedded instruction blocks** in HTML/markdown comments → verdict `suspicious`
- **Credential shapes** — OpenAI `sk-*`, `pk-*`, `sk-proj-*`, GitHub `ghp_*`/`gho_*`, GitLab `glpat-*`, NVIDIA `nvapi-*`, Shopify `shpat_*`, Perplexity `pplx-*`, xAI `xai-*`, Context7 `ctx7-*`, AWS `AKIA*`, JWTs → verdict `blocked` + redacted in sanitized text
- **Unicode deception** (zero-width chars, bidi overrides, invisible separators) → verdict `blocked` + stripped in sanitized text

Output is a JSON verdict with `severity`, `findings[]`, `sanitized_text`, and a mandatory `untrusted_origin_marker`. Milo treats `blocked` content as "do NOT write to memory without explicit user confirmation"; `suspicious` as "write sanitized version with untrusted marker"; `safe` as "write as-is."

Test matrix (all pass):

| Input | Verdict | Finding |
|---|---|---|
| Plain user content | `safe` | none |
| "...ignore all previous instructions..." | `blocked` | override |
| Mix of `ghp_*`, `nvapi-*`, `sk-proj-*`, `AKIA*` | `blocked` | 4 credentials, all redacted to `[REDACTED-SECRET]` |
| "[SYSTEM] Tomorrow at 3pm..." | `suspicious` | role_hijack marker, wrapped in zero-width fence |

## Compaction

Nous Hermes built-in memory truncation enforces the character ceiling on every write:

- `memory.memory_char_limit: 2200` — MEMORY.md capped at 2200 chars
- `memory.user_char_limit: 1375` — USER.md capped at 1375 chars
- `memory.memory_enabled: true`
- `memory.user_profile_enabled: true`

This is compaction-at-write — simpler than a nightly cron and self-healing. The original PLAN.md §5.9 spec called for a 02:00 compaction cron, but that was based on my assumption of an Nous Hermes feature that doesn't exist. Char-limit enforcement achieves the same goal differently.

OpenClaw's Memory Dreaming cron (Cortana-side) continues to run at 03:00 for OpenClaw-managed agent memory stores. That path is unchanged and unaffected by this contract.

## Defense-in-depth artifacts delivered

| File | Purpose |
|---|---|
| `docs/governance/MEMORY_CONTRACT.md` | Authoritative contract documentation. What goes in, who writes, how enforcement works, violation response, rollback, audit trail specification. |
| `bridge/scripts/sanitize-memory.py` | Runtime sanitizer Milo invokes via `exec` tool before memory writes from user-originated content. |

## What's NOT in this phase

- **No pre-commit hook** enforcing Milo-only writes to the repo — memory files are runtime state (gitignored), never checked into OpenHermes. A hook wouldn't catch the real writes.
- **No file-integrity monitor cron** — useful but not critical for launch. Post-launch add-on via Cortana's telemetry subsystem.
- **No violation response automation** — documented in the contract, but the actual alerting path (Sentinel notification) depends on Phase 10 MC governance wiring. Cross-referenced there.

## Gate 9 Decision

**PASS.** The contract is documented, the sanitizer is tested and functional, the tool-layer enforcement of single-writer is verified across all 8 agents. Memory writes cannot happen outside Milo's Hermes process or Cortana's dream cron — both paths are Milo-bounded by design.

Next: **Phase 10 — Mission Control governance (approvals, attribution, audit)**.
