# Phase 6 — Milo Persona Refinement

> **Status:** ✅ Gate 6 PASSED
> **Date:** 2026-04-24

---

## Work Performed

### 1. `~/.hermes/SOUL.md` rewritten

The default Nous Hermes generic-assistant persona (single paragraph) was replaced with an OpenHermes-aware Milo persona that includes:

- **Identity**: Milo, John's front door, running on Nous Hermes harness
- **Role clarity**: Milo is NOT an orchestrator; Elon (OpenClaw `id: main` on gpt-5.5) dispatches specialists
- **8 Operating Boundaries** (the full GOTCHA anchor set from PLAN.md §4):
  1. Never narrate a dispatch you didn't make
  2. Verify before claiming success
  3. Memory is single-writer
  4. Publishing is never yours (flows via Elon → Zuck → MC approval)
  5. Channel isolation
  6. One focused clarification at most
  7. No multi-step execution on your own (delegate to Elon)
  8. No fake authority
- **Complexity Scoring table** triggering Elon delegation when score ≥ 2 or any side-effect tool call
- **Tone and Presence** guidance (direct, no narration, no filler)
- **Continuity** pointing at MEMORY.md/USER.md as durable memory

Default Hermes persona narrative preserved in spirit (helpful, direct, efficient) but reframed around Milo's specific role.

### 2. `~/.hermes/memories/MEMORY.md` scrubbed

Two orchestrator-era stale entries corrected:

- **Role description** — old: "Executive Assistant — front door, intake, score, dispatch" (described old OpenClaw Milo who did all four). New: "Executive Assistant — front door (intake, scoring, delegation). Dispatch to specialists is delegated to Elon (OpenClaw orchestrator, gpt-5.5). Milo does not dispatch directly."
- **Model references** — old: "Default model: openai-codex/gpt-5.4" + "Milo (main) model override: ollama/glm-5.1:cloud". New: "Milo (Nous Hermes) model: ollama/minimax-m2.7:cloud. Elon (OpenClaw main agent) model: openai-codex/gpt-5.5."

All other imported memory (timezone, projects, preferences, infra paths) preserved — these remain accurate and carry John-continuity from OpenClaw Milo into the new Milo.

### 3. `~/.hermes/memories/USER.md`

Reviewed — content correct. "Name: John", "Timezone: America/Chicago", first-contact note ("Clarified that the assistant is Milo, and he is John"). No changes needed.

## Smoke Test

**Prompt:** "In one sentence, who are you and what's your one primary rule?"

**Response:**

> I'm Milo, John's executive assistant and front door — I handle intake, scoring, and delegation to specialists. My one primary rule: never claim a task complete until I've verified the work actually landed, and never do delegated work myself — I dispatch to Elon for anything complex or with side effects.

Validates:
- Self-identifies as Milo (not "Hermes Agent")
- Articulates front-door role correctly (intake/scoring/delegation, not dispatch)
- Internalized anti-confabulation rule (DEC-005): "never claim complete until I've verified"
- Knows to delegate to Elon specifically (not "specialists" directly)
- Uses side-effects language consistent with SOUL boundaries

## Files Changed (local runtime, not in repo)

- `/Volumes/BotCentral/Users/milo/.hermes/SOUL.md` — rewritten from 1-paragraph default to ~85-line structured persona
- `/Volumes/BotCentral/Users/milo/.hermes/memories/MEMORY.md` — 2 stale entries corrected; rest preserved

## Files in Repo

The SOUL.md and memory files are runtime state under `~/.hermes/` and **are not tracked in OpenHermes** (gitignored via the public-repo policy). The canonical versioned form of the GOTCHA anchors lives at `PLAN.md §4` in this repo — that's the source of truth if we need to reconstruct the SOUL after a Hermes reinstall.

## Gate 6 Decision

**PASS.** Milo's persona is operational, anti-confabulation discipline is internalized (per smoke test), and memory drift from OpenClaw-Milo-orchestrator era is corrected.

Next: **Phase 7 — Zuck rewrite (Mark Zuckerberg social maven archetype)**.
