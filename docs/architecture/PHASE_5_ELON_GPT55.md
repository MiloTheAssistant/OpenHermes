# Phase 5 — Elon on GPT-5.5 via Codex OAuth

> **Status:** ✅ Gate 5 PASSED (core milestone). One plan revision + one promotion from Evaluation Pool.
> **Date:** 2026-04-24

---

## Canary Results

| Canary | Model | Status | Duration | Output |
|---|---|---|---|---|
| Elon primary | `openai-codex/gpt-5.5` | ✅ | 9.5s | `ELON_GPT55_OK` |
| Elon tier-2 (planned: `gpt-5.5-mini`) | `openai-codex/gpt-5.5-mini` | ❌ | 23s | *"The 'gpt-5.5-mini' model is not supported when using Codex with a ChatGPT account"* |
| Kimi K2.6 benchmark | `ollama/kimi-k2.6:cloud` | ✅ | 15s | `def reverse_string(s): return s[::-1]` — exact instruction compliance |
| DeepSeek V4-flash benchmark | `ollama/deepseek-v4-flash:cloud` | ⚠️ | 13s | Correct code wrapped in markdown (violated "no markdown" instruction) |

## Critical Finding: gpt-5.5-mini Not Available via Codex OAuth

ChatGPT Pro Codex OAuth auth exposes `openai-codex/gpt-5.5` but **not** `openai-codex/gpt-5.5-mini`. Running the tier-2 canary returned:

> `{"detail":"The 'gpt-5.5-mini' model is not supported when using Codex with a ChatGPT account."}`

**Implications:**
- Our planned gpt-5.5 → gpt-5.5-mini → glm-5.1 three-tier cascade is blocked at tier-2.
- gpt-5.5-mini is only available via the standard OpenAI API (requires separate API key + billing).
- Staying on Codex OAuth means tier-2 must come from a different provider.

**Resolution:** Promote Kimi K2.6 from the Evaluation Pool to Elon's tier-2 fallback. The benchmark demonstrated:
- Correct output
- Exact instruction compliance ("no markdown" honored)
- Cross-provider failure-domain diversification (Ollama Pro, not Codex)
- Same subscription as Zuck (no incremental cost)

## Revised Elon Fallback Chain

| Tier | Model | Provider | Purpose |
|---|---|---|---|
| Primary | `openai-codex/gpt-5.5` | ChatGPT Pro Codex OAuth | Full orchestration capability (1M context, reasoning) |
| Tier-2 | `ollama/kimi-k2.6:cloud` | Ollama Pro | Cross-provider fallback when Codex is rate-limited or down; 1T params, 262k ctx, multimodal + thinking |
| Tier-3 | `zai/glm-5.1-turbo` | Z.ai GLM Coding Plan Pro | Independent failure domain (Codex AND Ollama Pro both down) |

## DeepSeek V4-flash Status

Benchmark returned the correct function but wrapped it in markdown code fence despite the explicit "no markdown" instruction. Output correctness: ✅. Instruction-following: ⚠️.

**Decision:** Keep in Evaluation Pool. A longer-context benchmark (multi-document synthesis for Sagan's long-doc lane) is the real test — instruction-following on a trivial single-line task isn't decisive. Pending Phase 5+ benchmark with real research workload.

## Gate 5 Decision

**PASS** with documented caveats:
- Elon on gpt-5.5 validated end-to-end
- Tier-2 promoted to `ollama/kimi-k2.6:cloud` (replacing dead gpt-5.5-mini path)
- Tier-3 `zai/glm-5.1-turbo` registered (not yet canary-tested — pending rate-limit simulation)
- Elon's SOUL rewrite (the anti-confabulation discipline update) deferred to Phase 6 combined pass with Milo's persona work

## Configuration Landed

`~/.openclaw/openclaw.json` updates:
- `agents.defaults.model.primary: openai-codex/gpt-5.5`
- `agents.defaults.models` registry: added `openai-codex/gpt-5.5`, `gpt-5.5-mini` (registered for completeness but won't work via OAuth), `kimi-k2.6:cloud`, `deepseek-v4-flash:cloud`, `gemma4:31b-cloud`, `glm-5.1:cloud`, `minimax-m2.7:cloud`, `zai/glm-5.1-turbo`, etc.
- `agents.list[main]`: `name: Elon`, `model: openai-codex/gpt-5.5`
- `agents.list[kat]`: `model: openai-codex/gpt-5.5` (was `openai/gpt-5.4` stale)
- `plugins.allow`: added `codex`, `nvidia`, `xai`

Schema note: OpenClaw's agent schema does not accept a `fallback_models` key at the agent level. Fallback behavior is managed via `openclaw models fallbacks` (separate subsystem) — left for follow-on config. For now, Elon runs on the primary and would fail explicitly rather than auto-failover until that's wired up.

## Evaluation Pool Status (Post-Phase-5)

| Model | Status after Phase 5 |
|---|---|
| `ollama/kimi-k2.6:cloud` | **PROMOTED** → Elon tier-2 fallback (committed) |
| `ollama/deepseek-v4-flash:cloud` | Still in Evaluation Pool; pending long-doc benchmark for Sagan candidate role |

Next: **Phase 6 — Milo persona refinement (SOUL anchor injection into Nous Hermes)**.
