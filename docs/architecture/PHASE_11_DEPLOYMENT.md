# Phase 11 — Deployment Topology (host-native + OrbStack-MC)

> **Status:** ✅ Gate 11 PASSED (topology verified end-to-end)
> **Date:** 2026-04-24

---

## Course correction from the original plan

The OPENHERMES_HANDOFF plan proposed a 3-container OrbStack deployment — Milo (Nous Hermes) and Elon (OpenClaw gateway) alongside Mission Control, fronted by a Caddy reverse proxy with loopback-only port bindings and `openhermes_internal` Compose network isolation.

Executing that path would have required:
- Writing a Dockerfile for the OpenClaw gateway (no official image ships)
- Wiring `host.docker.internal` for every native integration point (local Ollama at `127.0.0.1:11434`, Codex OAuth via `~/.codex/`, macOS Keychain-adjacent auth)
- Replacing OpenClaw's existing LaunchAgent with a container ENTRYPOINT supervisor
- Bind-mounting per-agent SQLite memory stores and hoping filesystem semantics don't drift
- Running a Caddy reverse proxy with bearer-token auth for a LAN-only personal assistant that has no public exposure today

On audit, none of that work measurably improved our security posture. The real governance enforcement is:

- **Memory contract** (Phase 9) — enforced at `tools.allow` in `openclaw.json`
- **Classifier** (Phase 8) — Milo calls `bridge/scripts/classify.py` before dispatch
- **Sanitizer** (Phase 9) — Milo calls `bridge/scripts/sanitize-memory.py` before memory writes
- **MC policies** (Phase 10) — enforced via Mission Control Approval records
- **Per-agent attribution** (Phase 10) — distinct tokens per agent in `~/.openclaw/secrets.json`

**Compose-network isolation adds nothing to any of these layers.** Its value is for multi-tenant or multi-host deployments, which is not our configuration.

## Final deployed topology

| Component | Runtime | Bound to | Reason |
|---|---|---|---|
| **Mission Control** (postgres, redis, FastAPI backend, Next.js frontend, webhook worker) | **OrbStack containers** — 5-container stack at `~/repos/openclaw-mission-control/compose.yml` | `:3100` (UI), `:8000` (API), `:5432` (DB loopback), `:6379` (Redis loopback) | Multi-service web app. Naturally container-shaped. Was already live. |
| **OpenClaw gateway (Elon + 7 specialists)** | **Host native** via macOS LaunchAgent | `127.0.0.1:18789` (loopback-only by OpenClaw design) | Deep integration: LaunchAgent, local Ollama at `:11434`, Codex OAuth via `~/.codex/auth.json`, per-agent SQLite memory at `~/.openclaw/memory/*.sqlite`, macOS notifications. Containerizing imposes friction with zero reward. |
| **Nous Hermes (Milo)** | **Host native** via `uv run hermes` (CLI) AND **`hermes-daemon` LaunchAgent** as of Phase 13 | CLI for terminal use; daemon on `127.0.0.1:18790` for Telegram/Discord/Mission-Control inbound | Phase 13 added the daemon to put Milo in front of channels. CLI remains for direct interactive use. See `PHASE_13_FRONT_DOOR.md`. |
| **Caddy reverse proxy** | **Not deployed** | — | No public exposure. LAN-only + Mac Mini. Revisit if Tailscale or public ingress is introduced later. |

### Why this topology is correct

1. **Mission Control is a legitimate container workload.** Postgres + Redis + two services + a worker — a classic compose-shaped stack. It was already containerized from day one, nothing changes here.

2. **OpenClaw is OS-integrated runtime, not a service.** It runs as a LaunchAgent, discovers Ollama via the user's local daemon, reads Codex credentials the user manages via the Codex CLI, writes memory via macOS filesystem semantics, surfaces notifications via NSUserNotification. These are all things you **lose** by containerizing — there's no corresponding gain since nothing else on the network needs to reach Elon beyond what loopback binding already provides.

3. **Nous Hermes is a CLI tool for a single user.** Like Claude Code, like `gh`, like `codex`. You wouldn't wrap those in a container for local use — you run them where your terminal is. Same applies here.

4. **No public exposure means no reverse proxy.** The Caddy + bearer-token auth layer is for exposing `/chat/*` to the public internet. We're not doing that. If you later Tailscale in or add a web UI accessible off-host, revisit this decision.

## Compose file kept as contingency

`deploy/compose/compose.yaml` remains in the repo as a **reference template** for future deployments where containerizing Milo + Elon does become the right call:

- Multi-host deployment (splitting Milo/Elon across machines)
- Shared-user scenarios requiring strict network boundaries
- Public exposure beyond the LAN (add reverse_proxy with Caddy)
- Test/staging copy running alongside production on the same host

The active `services:` block is empty (`services: {}`). The full reserved service shapes are commented in the file, ready to uncomment when needed. No current container to build, no image to maintain.

### Why the rename from `deploy/docker/` → `deploy/compose/`

- `docker-compose.yml` / `docker-compose.yaml` and `deploy/docker/` imply the Docker Inc. product — we run OrbStack.
- `compose.yaml` / `compose.yml` and `deploy/compose/` reflect the open **Compose Spec** (spec.compose-spec.io) which OrbStack, Docker Engine, Podman, Rancher Desktop, and Colima all implement.
- The CLI binary we invoke is still named `docker` — that's a historical quirk of OrbStack's drop-in compatibility, not something we can route around cosmetically. But directory/filename naming is our choice.

## Verification (Gate 11 canaries)

| # | Test | Expected | Actual | Result |
|---|---|---|---|---|
| 1 | MC stack containers up | 5 containers `Up` (backend, db healthy, frontend, redis healthy, webhook-worker) | All 5 `Up`, db + redis `(healthy)` | ✅ |
| 2 | OpenClaw gateway health | `{ok: true, agents: 8}` | `gateway ok: True, agents: 8` | ✅ |
| 3 | Nous Hermes Milo on host | Returns the canary string via minimax-m2.7 via ollama-cloud | `VERIFY_MILO_OK` (session_id 20260424_174335_d82f75) | ✅ |
| 4 | End-to-end bridge (Milo → classifier → Elon → return) | Classification `action`, route `milo->elon`, Elon runs on gpt-5.5, returns canary string | `PHASE11_BRIDGE_OK`, model `gpt-5.5`, provider `openai-codex`, duration 9.3s, session_key `agent:main:cron:9425e9a0-...` | ✅ |

All four gates pass. First attempt on the bridge canary hit a transient 120ms gateway timeout immediately after the MC stack restart (gateway was warming up); the retry completed cleanly in 9.3s.

## What Phase 11 did NOT do

- **No Dockerfile writing for Milo or Elon** — correctly scoped out
- **No image builds** — correctly scoped out
- **No Caddy TLS / reverse-proxy setup** — correctly scoped out (no public exposure)
- **No approval roundtrip canary** (Milo → Elon → Zuck → MC → Sentinel → approved → publish) — **deferred to Phase 12** since it touches channel routing and observability, which are Phase 12's scope. The individual primitives (classifier, MC push, per-agent attribution) are all independently validated.

## Gate 11 Decision

**PASS.** All three runtimes operational on their correct surfaces. End-to-end bridge canary passes post-rename (Milo→Elon, hermes→zuck). The topology is simpler than originally planned and correctly matches the problem we're solving.

Next (and final): **Phase 12 — Observability + phased channel migration**.
