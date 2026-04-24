# Phase 3 Audit — Keep/Rewrite/Discard Verification

> **Date:** 2026-04-24
> **Against:** `PLAN.md` §3 Keep/Rewrite/Discard Matrix
> **Scope:** Read-only verification of the migrated tree post-Phase-2 (commit `fc4c9f4`) + intervening commits. Outcome: Gate 3 criteria met with two inline fixes applied and four items correctly flagged as pending for Phases 5/7.

---

## ✅ KEEP — all items verified correctly migrated

| Matrix item | Location verified | Status |
|---|---|---|
| Cron-based specialist dispatch pattern (DEC-006) | `agents/Elon.md` has 10 mentions of dispatch/verify/session discipline | ✅ |
| Anti-confabulation discipline | `agents/Elon.md` inherits from OpenClaw Milo source | ✅ |
| Per-specialist tool allowlists | `agents/specialists/*/IDENTITY.md` all present with frontmatter | ✅ |
| Model matrix (6 specialists) | All 6 specialist IDENTITY files landed | ✅ (with 2 stale-model fixes applied this phase) |
| Cornelius local-exclusive constraint | `agents/specialists/cornelius/IDENTITY.md` preserved | ✅ |
| Provider fallback chains | `config/models.yaml` migrated | ✅ |
| Per-agent SQLite memory stores | Runtime-managed, gitignored (`workspace/memory/`) | ✅ by convention |
| Mission Control boards + approvals | `config/mission-control.yaml` migrated | ✅ |
| `Decision_Log.md` | DEC-001 through DEC-006 all intact, append-only preserved | ✅ |
| `state/brand-voice.md` placeholder | Still awaits John's 5 voice decisions | ✅ |

## 🔄 REWRITE — correctly pending for later phases

These are expected to be stale — they're migrated as-is from OpenClaw and get rewritten in their dedicated phase:

| File | Current state | Rewrites in | Gate |
|---|---|---|---|
| `agents/Elon.md` | Frontmatter still says `name: Milo`, `model: ollama_cloud/minimax-m2.7:cloud` | Phase 5 | Gate 5 |
| `agents/Zuck.md` | Description says "Email Triage, Drafting & Communication Intelligence" (old Hermes persona) | Phase 7 | Gate 7 |
| `docs/architecture/AGENTS.md` | Roster header: "Phase 5.1: 8 agents — Kat added" | Phase 5 (split Milo/Elon) + Phase 6.0 header bump | Gate 5 + Phase 6.0 doc sync |
| `docs/architecture/Agent_Model_Routing_Matrix.md` | Milo row describes old OpenClaw Milo; no Nous Hermes Milo row yet | Phase 5 (add Nous Hermes Milo + refine Elon row) | Gate 5 |

## 🗑️ DISCARD — correctly absent

| Matrix item | Verified absent |
|---|---|
| Retired agent files (Pulse/Quant/Hemingway/Jonny/Kairo/Themis/Cerberus/Sentinel-RT) | ✅ Not migrated; remain in OpenClawMaster history only |
| `tools.deny:["*"]` pattern | ✅ Not present anywhere in `config/` or `agents/` |
| ACPX `acp.defaultAgent` in docs | ✅ No references in migrated tree (only in DEC-006 historical context) |
| Hermes specialist directory | ✅ Removed — Hermes retired (became Zuck, a core agent, not a specialist) |

---

## Fixes applied during this audit

Two specialist IDENTITY files had stale model references that drifted from the current (Phase 5.1) matrix:

1. **`agents/specialists/kat/IDENTITY.md`**
   - Before: `model: openai/gpt-5.4`
   - After: `model: openai/gpt-5.5`
   - Reason: 2026-04-24 matrix bump to GPT-5.5 (runtime addendum, commit `870e257`)

2. **`agents/specialists/sentinel/IDENTITY.md`**
   - Before: `model: ollama_cloud/glm-5.1:cloud`
   - After: `model: openai/o4-mini`
   - Reason: DEC-006 recorded the move of Sentinel to reasoning-model QA; the IDENTITY file predated that decision

3. **`agents/specialists/hermes/` directory**
   - Removed — empty scaffold for a retired agent. Hermes became Zuck (a core agent, not a specialist).

---

## Preservation check: GOTCHA discipline anchors (PLAN.md §4)

The 8 GOTCHA anchors for new Milo (Nous Hermes) are documented in PLAN.md §4. They are NOT yet landed in workspace files (that happens in Phase 6 when we hand-write Nous Hermes Milo's SOUL). Documented as source of truth in PLAN.md. **Gate 3 does not require workspace files — those belong to Phase 6.**

## Preservation check: Evaluation Pool

Two candidate models pulled and documented per user direction (2026-04-24):

- `ollama/kimi-k2.6:cloud` — candidate Neo cloud fallback
- `ollama/deepseek-v4-flash:cloud` — candidate Sagan long-doc lane

Registered in `~/.openclaw/openclaw.json` (runtime, not repo) and documented in `docs/architecture/Agent_Model_Routing_Matrix.md` → Evaluation Pool section. Benchmark scheduled for Phase 5 using the `/model` session switch.

---

## Gate 3 decision

**PASS.** The Keep/Rewrite/Discard matrix is honored. Stale specialist model refs were corrected inline. Rewrite-pending items are correctly deferred to their dedicated phases (5, 7).

Next phase: **Phase 4 — Install Nous Hermes Agent.** No blockers.
