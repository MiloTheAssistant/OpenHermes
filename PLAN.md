# OpenHermes — Integration & Launch Plan

> **Status:** Phase 0 complete (preflight). Phase 1 pending user confirmation to proceed with public-repo creation.
> **Source-of-truth authority:** This repo supersedes `github.com/MiloTheAssistant/OpenClawMaster`. OpenClawMaster will be deleted after OpenHermes is live.
> **Execution model:** Claude Code holds the ball until OpenHermes is live and running. User holds gate approvals.
> **Non-destructive guarantee:** The live OpenClaw runtime (gateway on 18789, MC on 3100) continues to serve traffic throughout the migration. Cutover to the new architecture happens only at Phase 11.

---

## 1. Mission

Build an integrated environment where:

- **Milo** — Nous Hermes Agent — is the public-facing front door. Conversational interface, memory owner, MCP surface, inbox triage, channel router.
- **Elon** — OpenClaw orchestrator (formerly OpenClaw Milo) — is the dispatch/HALT/complexity-scoring core. Routes specialist work, enforces governance.
- **Zuck** — Social Media Maven (formerly OpenClaw Hermes) — is the sole publisher. Platform-native social voice in the Mark Zuckerberg archetype.
- **Specialists** — Sagan, Neo, Kat, Sentinel, Cortana, Cornelius — dispatched by Elon via the cron-based path validated in DEC-005/006.
- **Mission Control** (`localhost:3100`) — governance layer for approvals, audit, and attribution.

Two-layer boundary is hard:
- Milo handles intake and user conversation. Milo delegates everything with score ≥ 2 or any side-effect tool call to Elon.
- Elon dispatches specialists, compiles results, returns to Milo for delivery.
- Zuck is memory-firewalled — receives only `publish_packet` artifacts from Elon.

---

## 2. Architecture Snapshot

### Agent roster (9 agents, Phase 6.0)

| Agent | Role | Model | Runtime |
|---|---|---|---|
| **Milo** | Front door (NEW — Nous Hermes Agent) | `minimax-m2.7:cloud` primary, NIM fallback | `nousresearch/hermes-agent` Python (uv) |
| **Elon** | Orchestrator (formerly OpenClaw Milo) | `openai/gpt-5.4` via OAuth proxy, `gpt-5.4-mini` tier-2, `zai/glm-5.1` tier-3 | OpenClaw agent `id: elon` |
| **Zuck** | Social publisher (formerly OpenClaw Hermes) | `ollama/glm-5.1:cloud`, `zai/glm-5.1-turbo` fallback | OpenClaw agent `id: zuck` (renamed from `hermes`) |
| Sagan | Deep research | `perplexity/sonar-reasoning-pro`, `gpt-5.4` long-doc escalation | OpenClaw specialist |
| Neo | Lead engineer | `nim/qwen3-coder-480b`, `gpt-5.4` escalation, local `qwen3.6:35b` fallback | OpenClaw specialist |
| Kat | Content writing | `openai/gpt-5.4`, `ollama/gemma4:31b-cloud` fallback | OpenClaw specialist |
| Sentinel | QA gate | `openai/o4-mini`, `zai/glm-5.1-turbo` fallback | OpenClaw specialist |
| Cortana | State/memory/telemetry | `ollama/qwen3.5:4b` (local), `glm-5.1:cloud` fallback | OpenClaw specialist (persistent session) |
| Cornelius | Infra/heavy coding | `ollama/qwen3-coder-next:latest` (local 51GB exclusive) | OpenClaw specialist |

**Retired (do not reactivate):** Pulse, Quant, Hemingway, Jonny, Kairo, Themis, Cerberus, Sentinel-RT. Reference-only in OpenClawMaster history.

**Blocked provider:** Anthropic API — policy conflict with OpenClaw harness. Do not use for any agent.

### Resource topology

- **Ollama Pro cloud (3 concurrent slots):** Slot 1 Milo (minimax-m2.7:cloud), Slot 2 Zuck (glm-5.1:cloud), Slot 3 Kat fallback (gemma4:31b-cloud)
- **NIM:** Neo primary (qwen3-coder-480b), Sagan escalation (nemotron-ultra-253b)
- **Codex (OAuth proxy on 127.0.0.1:10531):** Elon primary (gpt-5.4), Sentinel primary (o4-mini), Kat primary (gpt-5.4), Milo/Sagan/Neo escalation
- **Z.ai GLM Coding Plan Pro:** Elon tier-3 (glm-5.1), Sentinel/Hermes fallback (glm-5.1-turbo)
- **Perplexity:** Sagan primary (sonar-reasoning-pro)
- **Local (Mac Mini M4 Pro, 64GB, 45GB budget):** Cornelius exclusive (51GB), Cortana (3.4GB), Neo local fallback (23GB)

### Dispatch mechanism (validated)

Elon uses OpenClaw's `cron` tool with `sessionTarget: "isolated"` + `agentId: "<specialist>"` per DEC-006. This creates a real `agent:<specialist>:cron:*` session on the specialist's configured model. Session-key verification is mandatory — any session key of the form `agent:main:subagent:*` is a failed dispatch and MUST be reported as such, never narrated as success.

The Milo↔Elon boundary uses the bridge: Milo exposes MCP tools to Elon; Elon is an OpenAI-compatible delegation target for Milo (via `base_url: http://openclaw:18789/v1`). Specialists talk to Elon only — never to Milo directly.

---

## 3. Keep / Rewrite / Discard Matrix (Phase 5.1 → 6.0)

### ✅ KEEP (migrate as-is from OpenClawMaster)

- Cron-based specialist dispatch pattern (DEC-006 fix — proven via canaries 1+2)
- Anti-confabulation discipline: session-key verification; never narrate a dispatch you didn't make
- Per-specialist tool allowlists (Sagan: web + memory read; Cortana: state only; Sentinel: read-only; Neo/Cornelius: engineering toolkit; Kat: content tools)
- Model matrix (Sentinel=o4-mini, Kat=gpt-5.4, Sagan=sonar-reasoning-pro, Neo=NIM 480b, Cornelius=local 48GB exclusive)
- Cornelius local-exclusive constraint (enforce in Elon's dispatch layer)
- Provider fallback chains (registered and cleaned in Phase 5.1)
- Per-agent SQLite memory stores (9 stores: main/milo/elon/zuck/sagan/neo/kat/sentinel/cortana/cornelius)
- Mission Control boards + approvals infrastructure (MC is the governance layer — no AxonFlow)
- Decision_Log.md (DEC-001 through DEC-006, append-only; DEC-007 = OpenHermes launch)
- `workspace-kat/` structure, Kat's identity prompt, `state/brand-voice.md` (awaiting decisions)

### 🔄 REWRITE (migrate with transformation)

| From | To | Notes |
|---|---|---|
| `agents/Milo.md` (OpenClaw Milo, orchestrator) | `agents/Elon.md` | Renames Milo → Elon. Phase 5.1 dispatch discipline preserved. Model changes to `openai/gpt-5.4` via OAuth (tier-2: gpt-5.4-mini, tier-3: glm-5.1 via Z.ai). |
| `workspace/SOUL.md` (current Milo soul) | Split: `workspace-elon/SOUL.md` (inherits orchestrator discipline) + new `workspace/SOUL.md` for Nous Hermes Milo | Orchestration/HALT/complexity-scoring content goes to Elon; front-door intake content goes to new Milo. |
| `agents/Zuck.md` (currently has old Hermes persona) | `agents/Zuck.md` full rewrite | Mark Zuckerberg archetype. Social publisher only. No email triage (Milo handles inbox). |
| `AGENTS.md` | New Phase 6.0 roster + Milo/Elon split documentation | |
| `docs/Agent_Model_Routing_Matrix.md` | Updated matrix with Elon primary = gpt-5.4 + Milo Nous Hermes row | |

### 🗑️ DISCARD (clean slate on new Milo)

- OpenClaw Milo's "I dispatch to specialists" identity (Elon's job now)
- Old Hermes's email triage responsibility (moves to new Milo's tool surface)
- Old Hermes's social persona details (replaced by Zuck Mark Zuckerberg archetype)
- Retired agent files (Pulse/Quant/Hemingway/etc. — remain in OpenClawMaster git history, not carried to OpenHermes)
- `tools.deny:["*"]` patterns (Phase 5.1 fix — stays fixed)
- ACPX plugin config (`acp.defaultAgent`) — not needed, cron dispatch works

---

## 4. GOTCHA Discipline Carried Into New Milo (Nous Hermes)

Eight hard-prompt anchors for Nous Hermes Milo's SOUL.md / config. These are distilled from Phase 5.1 learnings and must survive the clean-slate migration:

1. **Never narrate a dispatch you didn't make.** (DEC-005 anti-confabulation — applies to Milo→Elon delegation exactly as it applied to old Milo→specialists.)
2. **Verify before claiming success.** After any tool call returning an identifier (session key, cron job ID, delivery receipt, MCP tool response), confirm the shape matches expectation. Don't assert completion from model inference.
3. **Memory is single-writer.** Milo writes `workspace/memory/MEMORY.md` and `USER.md`. No other agent writes these. Cortana owns `TELEMETRY.md` on a separate path.
4. **Publishing is never yours.** Milo has zero direct write access to public channels. Everything publishable flows: Milo → classifier → Elon → Zuck → Mission Control approval → publish.
5. **Channel isolation.** Content received on one channel (Telegram, Discord, email) does not leak to another unless the user explicitly routes it. Preserve context boundaries.
6. **One focused clarification at most.** When in doubt, ask once. Don't interrogate.
7. **No multi-step execution on your own.** Score ≥ 2 or any side-effect tool call → classifier → Elon. You are the front door, not the worker.
8. **No fake authority.** Don't claim permissions you don't have. Don't pretend to own decisions that belong to John or Elon.

These anchors go into `workspace/memory/SOUL.md` (Nous Hermes convention) as the "Boundaries" section. Nous Hermes's default persona hooks handle the rest of Milo's tone/voice.

---

## 5. Phase Gates

Each phase has an explicit entry state, steps, and exit gate. No phase proceeds without the gate confirmed.

### Phase 0 — Preflight ✅ COMPLETE

- Host: macOS 26.5, Node 25.8.1, Python 3.9.6 (uv handles 3.11+ via .venv), uv 0.10.12, gh 2.88.1, Git 2.50.1
- Container: OrbStack 2.1.1 active context, Docker 29.3.0 CLI
- GitHub: authenticated as `MiloTheAssistant`, `OpenHermes` repo does not yet exist (expected)
- OpenClaw: CLI 2026.4.15 (deferred update due to 2026.4.21 extension-deps bug — tracked), Companion App 2026.4.20
- OpenClawMaster working tree clean except for `.DS_Store` (ignored)

### Phase 1 — Create public OpenHermes repo

**Steps:**
1. Scaffold directory structure under `$OPENHERMES_ROOT/`
2. Write `.gitignore` (hardened — Codex brief #1)
3. Write `.pre-commit-config.yaml` + `.secrets.baseline` (Codex brief #2)
4. Write `LICENSE` (MIT) + initial `README.md` (Codex brief #9)
5. Commit PLAN.md (this file) + scaffold as initial commit
6. Run `gitleaks detect --no-git` + `detect-secrets scan` → must be clean
7. `gh repo create MiloTheAssistant/OpenHermes --public --source=. --remote=origin --push`
8. Enable secret scanning + push protection + Dependabot via `gh api` or UI

**Gate 1:** Repo exists at `github.com/MiloTheAssistant/OpenHermes`, public, scanners clean, push protection + secret scanning enabled, PLAN.md visible.

### Phase 2 — Migrate authoritative content from OpenClawMaster

**Intent:** `git mv` the authoritative OpenClawMaster content into OpenHermes. Preserve Git history via cross-repo import. OpenClawMaster becomes frozen.

**Migration inventory (what moves):**
- `AGENTS.md` → `docs/architecture/AGENTS.md`
- `GotchaFramework.md` → `docs/governance/GotchaFramework.md`
- `CLAUDE.md` → `docs/architecture/CLAUDE.md` (project context for future Claude Code sessions)
- `agents/*.md` → `agents/*.md` (Milo.md renamed to Elon.md in Phase 5)
- `config/*.yaml` → `config/` (sanitized for public exposure)
- `docs/*.md` → `docs/architecture/`, `docs/runbooks/`, `docs/governance/` (organized by kind)
- `state/Decision_Log.md` → `state/Decision_Log.md` (continuing append-only)
- `state/brand-voice.md` → `state/brand-voice.md` (awaiting decisions)
- `tools/scripts/*.sh` → `scripts/` (mc-push.sh, gateway-restart.sh, sync-decisions.sh)
- `state/Active_Projects.md`, `state/Artifacts_Index.md` → `state/`
- Workspace files (SOUL, BOOTSTRAP, HEARTBEAT, IDENTITY, MEMORY, USER, AGENTS templates) → `workspace/` (will be forked for Elon in Phase 5)

**Sanitization requirements (public repo):**
- Remove any hardcoded IPs, hostnames, production URLs, usernames (`milo`, email addresses)
- Replace with placeholders: `$OPENCLAW_HOST`, `admin@example.com`, `/path/to/workspace`
- Strip Mission Control board UUIDs from committed configs (move to secrets or env)
- Remove `milo` path references from scripts (parameterize via env)
- Validate with `gitleaks detect --no-git` after each batch

**Steps:**
1. Codex brief #10: `scripts/migration/move-from-openclawmaster.sh` — mechanical `git mv` wrapper with sanitization hooks
2. Run migration in batches (agents, config, docs, scripts) with gitleaks + detect-secrets between each
3. For each migrated file, add a migration header comment: `<!-- migrated from OpenClawMaster commit a48aa01 -->` where relevant
4. Append migration summary to `state/Decision_Log.md` as DEC-007
5. Add `LEGACY.md` to OpenClawMaster pointing at OpenHermes (last commit there)
6. Push to OpenHermes

**Gate 2:** All authoritative content present in OpenHermes, sanitized, scanners clean. Live OpenClaw runtime continues to function (it reads from `~/.openclaw/` local state, not the repo — so no runtime impact yet).

### Phase 3 — Preserve Phase 5.1 discipline

Already documented in Section 3 (Keep/Rewrite/Discard Matrix). This phase is the explicit audit: walk the migrated tree and confirm each entry in the matrix is honored. No new artifacts — this is a verification + correction phase.

**Gate 3:** User signs off on the Keep/Rewrite/Discard matrix as applied.

### Phase 4 — Install Nous Hermes Agent (new Milo)

**Steps:**
1. Clone sibling to OpenHermes: `git clone https://github.com/nousresearch/hermes-agent.git ../hermes-agent`
2. Check latest stable tag; pin that version; document in `docs/runbooks/NOUS_HERMES_VERSION.md`
3. `uv sync` inside `hermes-agent/`
4. Write `~/.hermes/config.yaml` with:
   - `identity.name: Milo`
   - `providers.primary: minimax-m2.7:cloud` via Ollama API
   - `providers.fallback: NIM minimax-m2.7`
   - `memory.path: ~/.openclaw/workspace-milo/memory` (or whichever path aligns with Nous Hermes conventions)
   - `mcp.server.enabled: true`
   - `approvals.mode: allowlist` + `on_miss: ask`
5. Provision `OLLAMA_API_KEY` + `NVIDIA_NIM_API_KEY` in `~/.hermes/env` (never in repo)
6. Smoke test: `hermes chat "Hello, who are you?"` → must identify as Milo with Nous Hermes-default persona

**Gate 4:** Nous Hermes runs standalone, smoke-test chat passes.

### Phase 5 — Complete Milo→Elon rename + Elon on GPT-5.4

**Steps:**
1. `git mv agents/Milo.md agents/Elon.md` (in OpenHermes; OpenClawMaster is already frozen)
2. Edit `agents/Elon.md` — update `name: Elon`, preserve all Phase 5.1 dispatch discipline
3. Fork `workspace/` → `workspace-elon/` with SOUL/BOOTSTRAP/HEARTBEAT/IDENTITY/MEMORY/USER/AGENTS files
4. Rewrite `workspace-elon/SOUL.md`: inherit orchestrator identity from current `workspace/SOUL.md` (which has our DEC-006 cron-dispatch rules baked in). Keep all anti-confabulation discipline.
5. New `workspace/SOUL.md` for Nous Hermes Milo: clean slate + the 8 GOTCHA anchors from Section 4 of this plan
6. Install `openai-oauth` proxy: `npm install -g openai-oauth`; first run triggers ChatGPT OAuth in browser
7. Write `deploy/launchd/com.openhermes.openai-oauth.plist` (Codex brief #7) to supervise proxy on boot
8. Additive edit to `~/.openclaw/openclaw.json`:
   - Add `models.custom_models` entries for gpt-5.4 (OAuth), gpt-5.4-mini (OAuth), glm-5.1 (Z.ai)
   - Update `agents.list` for `id: elon`: set `model: gpt-5.4`, `fallback_models: [gpt-5.4-mini, glm-5.1]`
   - Rename `id: hermes` → `id: zuck` (holds for Phase 7)
9. Backup first: `cp ~/.openclaw/openclaw.json ~/.openclaw/openclaw.json.bak-$(date +%Y%m%d-%H%M%S)`
10. Add `ZAI_CODING_PLAN_KEY` to `~/.openclaw/secrets.json` (chmod 600)
11. Restart gateway: `bash scripts/gateway-restart.sh`
12. Canary: cron-dispatch to Elon asking for a dry-run plan; verify session on gpt-5.4 and return path works

**Gate 5:** Elon boots on gpt-5.4 via OAuth, tier-2 and tier-3 fallbacks tested by simulated primary failure, no disruption to specialists.

### Phase 6 — Manual Milo persona migration

**Intent:** Nous Hermes doesn't have a `claw migrate` command. Migration is manual. Start with Nous Hermes's default persona; layer in the 8 GOTCHA anchors from Section 4; selectively preserve user-relationship details (John's name, timezone, channel preferences) extracted from OpenClaw Milo's workspace.

**Steps:**
1. Read `~/.openclaw/workspace/USER.md` (OpenClaw Milo's user context) — extract factual user details (name, timezone, channel preferences)
2. Write `~/.hermes/memories/USER.md` with those details — factual only, no inherited personality
3. Write `~/.hermes/memories/MEMORY.md` as empty/seed — new Milo starts fresh on memory
4. Write `~/.hermes/memories/SOUL.md` (if Nous Hermes uses that convention) or equivalent — default persona + Section 4 GOTCHA anchors
5. Review with user before any traffic is routed to new Milo

**Gate 6:** User confirms Nous Hermes Milo's persona + USER details before traffic flows.

### Phase 7 — Rewrite Zuck as Mark Zuckerberg social maven

**Steps:**
1. Full `agents/Zuck.md` rewrite. Archetype brief: social media maven, platform-native voice, confident but measured, fluent in Twitter/X, LinkedIn, Threads, Instagram mechanics. Zuck is the only agent that posts. All social content flows through Zuck.
2. Remove email triage from Zuck's scope (inbox → Milo; drafts → Kat; send → Milo).
3. Define Zuck's deliverable envelope: `publish_packet` with platform-scoped variants, hashtags, timing, audience signal.
4. Update `workspace-zuck/` (the OpenClaw workspace folder for zuck agent) bootstrap files with new persona.
5. Enforce memory firewall: Zuck's `tools.allow` in openclaw.json excludes all `milo.recall_memory` and any memory-read tools.
6. Smoke test: dispatch a Zuck cron task with a `publish_packet` and verify the output envelope.

**Gate 7:** User approves Zuck persona and `publish_packet` envelope shape before any channel wiring.

### Phase 8 — Bridge (Milo ↔ Elon)

**Steps:**
1. Codex brief #3: `bridge/schemas/handoff.schema.json` (JSON Schema Draft 2020-12, strict)
2. Write `bridge/scripts/classify.py` — deterministic classifier per the table in Section 6 (no LLM-driven routing)
3. Write `bridge/config/milo-mcp-plugin.json` for OpenClaw to register Milo as MCP tool source for Elon only
4. Write `bridge/config/elon-provider.yaml` (handoff provider config for Nous Hermes's `providers.delegation` section)
5. Additive entry in `~/.openclaw/openclaw.json`: register the milo-mcp-plugin
6. Test: Milo calls `milo.recall_memory` from Elon (MCP direction); Milo sends a handoff envelope to Elon (OpenAI-compatible direction)

**Gate 8:** Bridge roundtrip canary passes in both directions.

### Phase 9 — Single-writer memory contract

**Steps:**
1. Document in `docs/governance/MEMORY_CONTRACT.md`
2. Write `.githooks/pre-commit` rejecting direct writes to `workspace/memory/MEMORY.md` and `USER.md` by any process not running as Milo (enforced via commit-time check of the author/process)
3. Write `bridge/scripts/sanitize-memory.py` (prompt-injection sanitizer; runs on user-originated content before memory write)
4. Configure Nous Hermes nightly compaction cron (02:00 local): `memory.compaction_cron: "0 2 * * *"`
5. File integrity monitoring on `SOUL.md`, `AGENTS.md` reference, `MEMORY.md` — log every change

**Gate 9:** Contract enforced, sanitizer active, compaction scheduled.

### Phase 10 — Mission Control as governance layer

**Intent:** No AxonFlow. MC's existing approvals infra is the governance layer.

**Steps:**
1. Add governance policies to `governance/mission-control/policies.yaml`:
   - `deny_unapproved_publish`: any Zuck publish attempt requires MC approval from Sentinel (board lead)
   - `pii_scan_outbound`: scan + redact before any outbound to Zuck/Milo comms channels
   - `budget_enforcement`: enforce handoff envelope budget
2. Per-agent credentials for attribution (works around OpenClaw shared-MCP-creds issue #67682):
   - `ZUCK_TWITTER_TOKEN`, `ZUCK_LINKEDIN_TOKEN`, etc. in `~/.openclaw/secrets.json`
   - Plugin layer resolves calling agent via `x-openclaw-agent-id` header
3. Write `governance/audit/` append-only log destination
4. Weekly cron: SHA-256 checksum of audit log, committed to OpenHermes as tamper-evidence

**Gate 10:** MC approvals flow tested end-to-end for Zuck publish, per-agent credentials verified in audit log.

### Phase 11 — OrbStack deployment

**Steps:**
1. Codex brief #4: `deploy/docker/docker-compose.yml` + Caddyfile (OrbStack-compatible)
2. Codex brief #6: `.env.example` + `deploy/env/milo.env.example` + `deploy/env/elon.env.example`
3. Dockerfile for OpenClaw (or use external process; decide based on current runtime fit)
4. Dockerfile for Nous Hermes (derived from hermes-agent repo)
5. OrbStack networks: `openhermes_internal` (Milo ↔ Elon), `openhermes_edge` (public → proxy)
6. Loopback-only port bindings for gateway (18789) and Milo MCP (8787)
7. Caddy reverse proxy with token-header auth
8. `orbstack` up, verify all health endpoints, confirm network posture

**Gate 11:** Services run under OrbStack, external access gated through Caddy only.

### Phase 12 — Observability + phased channel migration

**Observability steps:**
1. Codex brief #5: `scripts/observability/log-collector.sh`
2. Install `elon-watch` health monitor (formerly `milo-watch`), rename configuration
3. Daily health report: uptime, memory integrity, governance violations, failed handoffs, budget exhaustion

**Channel migration order (72h stable between each):**
1. Local/browser chat (internal test)
2. Telegram DM (single test user)
3. Discord DM or test channel
4. Slack (internal workspace)
5. Email intake
6. Broader rollout

Each channel gets its own user-approval gate.

**Gate 12:** Each channel confirmed stable for 72h before proceeding. All observability streams reporting clean.

---

## 6. Deterministic Classifier (Bridge §8)

Milo cannot bypass this. The classifier sits between Milo's intake and any routing decision.

| Condition | `governance_class` | Required route |
|---|---|---|
| Internal message + no write tools requested | `info` | Milo answers directly, no Elon dispatch |
| Any file write, API call with side effects, or internal message send | `action` | Milo → Elon → specialist → Milo |
| Outbound to public social, email to external, blog post | `publish` | Milo → Elon → Zuck → Mission Control approval |
| Infra changes, secret rotation, deletions, financial actions | `irreversible` | Milo → Elon → Sentinel → Mission Control approval + explicit user confirm |

Classifier implementation: deterministic Python/TS rule engine in `bridge/scripts/classify.py`. Zero LLM calls in the classifier path.

---

## 7. Codex Offload Briefs

Run these in parallel Codex sessions while Claude Code executes the integration work. Each brief is self-contained.

### Brief #1 — Hardened `.gitignore`
```
Produce a hardened .gitignore for a PUBLIC GitHub repo (OpenHermes). Repo contents: Python (uv/.venv), Node (node_modules), Docker/OrbStack, macOS dev environment. Must aggressively block: all .env variants (allow .env.example only), *.pem/*.key/*.p12/*.pfx/*.crt, OAuth state dirs (.openai-oauth, .hermes/auth, .hermes/session), cloud creds (.aws, .gcp, .azure, gcp-key.json, aws-credentials, service-account*.json), IDE configs (.vscode/settings.json, .idea, .cursor), common token/apikey filename patterns, workspace memory files (workspace/memory/*.md except README + .gitkeep), audit logs (governance/audit/*.jsonl), build artifacts, coverage, test outputs, OS noise. Include section headers as comments.
```

### Brief #2 — `.pre-commit-config.yaml` + `.secrets.baseline` seed
```
Configure pre-commit hooks for a public repo. Hooks needed:
- gitleaks v8.21.2 (detect committed secrets)
- detect-secrets v1.5.0 with baseline support (exclude package-lock.json, .secrets.baseline)
- pre-commit-hooks v5.0.0: check-added-large-files (maxkb=1024), check-merge-conflict, detect-private-key, check-yaml, check-json, end-of-file-fixer, trailing-whitespace

Install both pre-commit and pre-push stages. Produce the complete .pre-commit-config.yaml plus install commands. Also produce a minimal empty .secrets.baseline seed file (initial state, no findings).
```

### Brief #3 — Handoff envelope JSON Schema
```
Produce a strict JSON Schema (Draft 2020-12) for the OpenHermes handoff envelope. Required fields:

- task_id: ULID string
- origin_agent: enum [milo, elon, zuck, sagan, neo, sentinel, cortana, cornelius, kat]
- target_agent: same enum
- request_summary: string, max 2000 chars
- governance_class: enum [info, action, publish, irreversible]
- routing_profile: string
- risk_level: enum [low, medium, high, critical]
- requires_halt: boolean
- budget: object {max_tokens int≥1, max_seconds int≥1, max_tool_calls int≥1}
- artifacts: array of objects
- status: enum [pending, in_progress, awaiting_approval, complete, halted, failed]
- next_action: string

Optional audit object: {created_at (ISO datetime), created_by (string), trace_id (string)}

additionalProperties: false. Include descriptive error messages on each field. Also produce a companion Python validator using `jsonschema` library that loads the schema, validates an envelope, and returns (is_valid, errors_list).
```

### Brief #4 — `docker-compose.yml` for OrbStack + Caddyfile
```
Produce a docker-compose.yml for OrbStack (macOS) with 3 services:
1. milo (build context: ../../../hermes-agent) — on networks openhermes_internal + openhermes_edge; volume mount workspace → /workspace rw; env file deploy/env/milo.env ro; expose 127.0.0.1:8787 loopback only
2. elon (build context: ../../../openclaw-master) — on openhermes_internal only; workspace → /workspace READ-ONLY; env file deploy/env/elon.env ro; expose 127.0.0.1:18789 loopback only
3. reverse_proxy (image: caddy:2) — on openhermes_edge; bind 443 public; mount Caddyfile ro

Networks: openhermes_internal (internal=true bridge), openhermes_edge (bridge).
restart: unless-stopped on all services.

Also produce the Caddyfile: authenticated reverse proxy that requires a bearer token header (env OPENHERMES_EDGE_TOKEN) and forwards to milo:8787 for /chat/* and rejects all other paths. Include TLS via Caddy's automatic HTTPS.
```

### Brief #5 — `scripts/observability/log-collector.sh`
```
Produce a bash script that tails the logs of 3 OrbStack containers (milo, elon, reverse_proxy) in parallel, prefixes each line with the container name + ISO timestamp, JSON-merges structured log lines (detect by leading `{`), and writes to stdout. Support optional SIEM forwarding via SIEM_ENDPOINT env var (curl POST NDJSON, retry on failure with backoff). Handle container restarts (re-attach on reconnect). Exit cleanly on SIGTERM.

Keep pure bash + jq. No node/python. Include usage comment at top.
```

### Brief #6 — `.env.example` + component env templates
```
Produce three files:
1. .env.example (root) — documents all required env vars with inline comments
2. deploy/env/milo.env.example
3. deploy/env/elon.env.example

Required vars (with comments explaining source):
- OLLAMA_API_KEY (from ollama.com account settings — Milo primary)
- NVIDIA_NIM_API_KEY (nvapi-... from build.nvidia.com — Milo fallback)
- ZAI_CODING_PLAN_KEY (from Z.ai dashboard — Elon tier-3 fallback)
- OPENCLAW_GATEWAY_TOKEN (generated in Phase 11)
- MILO_MCP_TOKEN (generated in Phase 8)
- OPENHERMES_EDGE_TOKEN (Caddy reverse proxy auth)
- ZUCK_TWITTER_TOKEN, ZUCK_LINKEDIN_TOKEN (per-agent attribution)
- MILO_GMAIL_TOKEN, MILO_SLACK_TOKEN (per-agent attribution)
- SIEM_ENDPOINT (optional — observability target)

Milo env should only include Milo-relevant vars. Elon env should only include Elon-relevant vars. Zero secrets, placeholder values only. Never committed: the .env counterparts.
```

### Brief #7 — launchd plist for OAuth proxy supervisor
```
Produce a macOS launchd plist at deploy/launchd/com.openhermes.openai-oauth.plist. Supervises the `openai-oauth` Node.js process (after `npm install -g openai-oauth`). Requirements:
- Auto-restart on failure
- Log stdout to ~/Library/Logs/openhermes/oauth-proxy.log
- Log stderr to ~/Library/Logs/openhermes/oauth-proxy.err.log
- Inherits user session env (for ChatGPT OAuth tokens)
- KeepAlive: only on crash (not on clean exit)
- Run at user login

Include install/uninstall instructions as comments at top (launchctl bootstrap / bootout pattern).
```

### Brief #8 — GitHub Actions workflow for secret scanning
```
Produce .github/workflows/secret-scan.yml. Workflow:
- Trigger: push to main, all pull requests
- Runs gitleaks on the full git history (not just diff) — fail on any finding
- Runs detect-secrets against .secrets.baseline — fail on any new unaudited finding
- On failure, posts a PR comment explaining the finding and next steps
- Uses ubuntu-latest runner

Include setup steps (checkout with fetch-depth 0, install gitleaks + detect-secrets). Use GitHub-hosted actions where possible.
```

### Brief #9 — `README.md` + `LICENSE` scaffold
```
Produce two files:

1. LICENSE — MIT license text, Copyright (c) 2026 MiloTheAssistant.

2. README.md (public-facing) — explain the OpenHermes architecture non-technically:
- What it is (integrated multi-agent environment)
- Two-layer architecture diagram (Milo front door, Elon orchestrator, Zuck publisher, specialists)
- What's in this repo (reference configs, bridge schemas, governance policies, runbooks)
- What's NOT in this repo (secrets, live memory, audit trails, user PII)
- How to read the plan (link to PLAN.md)
- Contribution status: reference-only; PRs not accepted during build phase
- Security disclosure: include a basic SECURITY.md pointer

Keep it concise. No operational details that reveal infrastructure. No live URLs.
```

### Brief #10 — Migration script `scripts/migration/move-from-openclawmaster.sh`
```
Produce a bash script that:
1. Takes $OPENCLAW_MASTER and $OPENHERMES_ROOT as env inputs (fail if missing)
2. Takes a manifest file path as arg (file with lines of format: "SOURCE_PATH TARGET_PATH" relative to each repo)
3. For each line: verify SOURCE_PATH exists in $OPENCLAW_MASTER, mkdir -p target parent in $OPENHERMES_ROOT, git mv equivalent via: copy file content + stage in OpenHermes + create entry in OpenClawMaster REMOVED manifest (for later cleanup step)
4. Run gitleaks detect on $OPENHERMES_ROOT after each batch of 10 files
5. Fail fast on: missing source, gitleaks finding, git conflicts
6. Log all moves to a migration-log.txt in OpenHermes

Keep it pure bash + git. Include usage example as comment. Safe to re-run (idempotent).
```

---

## 8. Open Decisions

Nearly all settled. Remaining items parked for post-launch:

1. **Shopify migration** — paused until OpenHermes is live
2. **Perplexity Sagan payload bug** — deferred (workaround: use gpt-5.4 long-doc lane for research)
3. **OpenClaw 2026.4.21 extension-deps upstream bug** — track but don't block
4. **Nous Hermes latest version** — pin at install time, document in `docs/runbooks/NOUS_HERMES_VERSION.md`
5. **Production secrets backend** (1Password / Doppler / AWS SM / Infisical vs `~/.openclaw/secrets.json`) — decide in Phase 11; personal deployment can use local secrets.json
6. **Email triage scope for new Milo** — scope confirmed (intake + routing; drafts → Kat; send via Milo)

---

## 9. Timeline Target

Metered pace. Days are sequential unless noted.

| Day | Target |
|---|---|
| Day 1 (today) | Phases 0 + 1 + 2 (preflight, repo create, migration) |
| Day 2 | Phase 3 (keep/rewrite/discard audit) + Codex brief results integrated |
| Day 3–4 | Phase 4 (Nous Hermes install + standalone smoke) |
| Day 5–6 | Phase 5 (Elon rename + GPT-5.4 OAuth + 3-tier fallback) |
| Day 7 | Phase 6 (Manual Milo persona migration) |
| Day 8 | Phase 7 (Zuck rewrite) |
| Day 9–10 | Phase 8 (Bridge + classifier) |
| Day 11 | Phase 9 (Memory contract) |
| Day 12 | Phase 10 (Mission Control governance) |
| Day 13–14 | Phase 11 (OrbStack deployment) |
| Day 15+ | Phase 12 (Observability + phased channels, 72h each) |

Full cutover including all channel migrations: ~3 weeks. Core dispatch + single channel: ~2 weeks.

---

## 10. Rollback Strategy

At any phase, if something breaks:

- **Before Phase 11 (no deployment):** OpenClawMaster runtime continues to serve. Roll back OpenHermes tree to last good commit. Re-evaluate.
- **During Phase 11 (deployment cutover):** OrbStack services can be stopped; OpenClaw on host continues serving; remove `.hermes/` directory, revert `openclaw.json` to backup, restart gateway. Return to Phase 5.1 state.
- **After OpenHermes is live:** Maintain OpenClawMaster runtime for 72h after full cutover as emergency fallback. Then delete.

The OpenClawMaster repo is the pre-migration snapshot — cloning it at any time recovers the previous state.

---

## 11. What Claude Code Must NOT Do

- Not modify the live OpenClaw runtime except for the three documented additive changes (Elon model entry, milo-mcp-plugin entry, workspace rename in openclaw.json) and only after their respective gates
- Not copy live `MEMORY.md` content from OpenClaw workspaces into OpenHermes (workspace files are gitignored)
- Not install ClawHub third-party skills without security review
- Not enable production channels before Gate 11
- Not merge Milo and Elon into a single runtime — the two-layer boundary is the architecture
- Not let Milo publish directly to public channels — always routes through classifier → Elon → Zuck → MC
- Not skip a gate to save time
- Not configure any agent to use Anthropic models (policy conflict)
- Not replace the OAuth proxy with scraped session tokens
- Not commit secrets, hostnames, PII, or live audit logs to this public repo
- Not disable or bypass pre-commit hooks
- Not push to main without running `gitleaks detect` first

---

## 12. Gate Sign-Off Log

Record each gate's approval here as they're passed.

| Gate | Description | User Approval | Date |
|---|---|---|---|
| 0 | Preflight complete | ✅ | 2026-04-22 |
| 1 | Public repo + scanners clean + protection enabled | Pending | — |
| 2 | Migration content moved + sanitized | Pending | — |
| 3 | Keep/Rewrite/Discard matrix honored | Pending | — |
| 4 | Nous Hermes Milo smoke-test pass | Pending | — |
| 5 | Elon on gpt-5.4 + 3-tier fallback | Pending | — |
| 6 | New Milo persona + USER migrated | Pending | — |
| 7 | Zuck rewrite + publish_packet envelope | Pending | — |
| 8 | Bridge roundtrip canary | Pending | — |
| 9 | Memory contract enforced | Pending | — |
| 10 | Mission Control governance end-to-end | Pending | — |
| 11 | OrbStack deployment live | Pending | — |
| 12 | Channels migrated + stable | Pending per channel | — |
