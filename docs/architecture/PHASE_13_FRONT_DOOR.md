# Phase 13 — Milo as Front Door (Hermes is Milo, gateway is Elon)

> **Status:** 🚧 In progress (scaffolding committed; daemon awaits first-run verification)
> **Date:** 2026-04-27

## Why this phase exists

The original architecture: Nous Hermes Agent framework (Milo) is John's front door; OpenClaw (Elon + 7 specialists) is the orchestration engine behind Milo. Phase 12 launched OpenHermes LIVE — but a drift had crept in:

- Discord and Telegram channel handlers were registered against the OpenClaw gateway's `main` agent (named "Elon" in Phase 5).
- The Companion App opened sessions directly against the gateway, bypassing Milo entirely.
- Mission Control Board Chat routed to gateway agents, fine for project work but not for personal-assistant traffic.
- The gateway's `~/.openclaw/workspace/SOUL.md` still said "You are Milo, Executive Assistant…" from before the Phase 5 rename — so when a Companion App session opened, the agent introduced itself as Milo, on `gpt-5.5`, contradicting the actual Phase 5 design.

Result: John saw "Milo on gpt-5.5" in the Companion App and correctly flagged the architectural collision. Phase 13 fixes it.

## Decisions

| ID | Decision |
|---|---|
| DEC-008 | Phase 13 launched — Hermes (Milo) is the only front door; gateway is Elon-only |
| DEC-009 | Telegram via long-polling, Discord via websocket gateway — no inbound tunnel |
| DEC-010 | Channel credentials migrated from `openclaw.json` to `~/.openhermes/milo-daemon.env` (mode 0600) |
| DEC-011 | OpenClaw Companion App retired as a chat surface |

## Changes

### 13.1 Gateway identity restored to Elon

- `~/.openclaw/openclaw.json` → `agents.list[id=main]` reverted to `name=Elon, model=openai-codex/gpt-5.5` (Phase 5 design).
- `agents.defaults.model.primary` reverted to `openai-codex/gpt-5.5`.
- Backup at `~/.openclaw/openclaw.json.bak-phase13-<ts>`.
- `~/.openclaw/workspace/SOUL.md` rewritten as Elon's operating contract: Elon is an engine, never speaks to John, returns result envelopes to Milo, single-writer for memory is Milo (not Elon).

### 13.2 Channel handlers re-routed to Milo daemon

| Channel | Phase 12 | Phase 13 |
|---|---|---|
| Telegram | OpenClaw `channels.telegram` → `main` agent | Disabled in OpenClaw; Milo daemon long-polls `getUpdates` |
| Discord | OpenClaw `channels.discord` → `main` agent | Disabled in OpenClaw; Milo daemon connects via discord.py websocket gateway |
| Companion App | → gateway `main` (Elon) | **Retired.** Not uninstalled; can be repointed later if desired |
| MC Board Chat | → board lead agent (gateway-internal) | Unchanged. Project work, not Milo's personal-assistant traffic |
| Mission Control approvals → Milo | Was: `mc-push` task, no Milo destination | New: MC posts to `POST 127.0.0.1:18790/notify` on the Milo daemon |
| Hermes CLI | `uv run hermes chat` ✅ | Unchanged ✅ |

### 13.3 New: `hermes-daemon/`

A small FastAPI service running as a LaunchAgent at `127.0.0.1:18790`. Loopback only.

| File | Purpose |
|---|---|
| `main.py` | FastAPI app + lifespan starting Telegram + Discord workers |
| `milo_bridge.py` | Sanitizer + Hermes CLI subprocess invocation per inbound turn |
| `telegram_poller.py` | `getUpdates` long-poll loop with allowlist enforcement |
| `discord_bot.py` | discord.py websocket client with guild + user allowlists |
| `settings.py` | env loader (reads `~/.openhermes/milo-daemon.env`) |
| `com.openhermes.milo.plist` | macOS LaunchAgent — KeepAlive on crash, throttle 10s |
| `requirements.txt` | fastapi, uvicorn, httpx, discord.py, python-dotenv |
| `README.md` | architecture + endpoint summary |

Endpoints:
- `GET /health` — used by `daily-health-report.sh`
- `POST /chat` — `{user_id, source, text}` → `{reply, duration_ms}`
- `POST /notify` — Mission Control approval-resolution sink

### 13.4 Phases 1–12 audit

| Phase | Status under Phase 13 | Action taken |
|---|---|---|
| 1 (repo) | ✅ unchanged | none |
| 2 (migration) | ✅ unchanged | none |
| 3 (audit) | ✅ unchanged | none |
| 4 (Hermes installed) | ✅ unchanged — Hermes SOUL already says "You are Milo" | none |
| 5 (Elon on gpt-5.5) | ✅ design correct, drift corrected | gateway main + SOUL restored |
| 6 (Milo persona) | ✅ unchanged — Milo persona lives in `~/.hermes/SOUL.md` | none |
| 7 (Zuck rewrite) | ✅ unchanged | none |
| 8 (bridge — classify + delegate) | ✅ becomes more central — every Milo turn now passes through it before Elon | sanitizer wired into daemon's `milo_bridge.py` |
| 9 (memory contract + sanitizer) | ✅ Milo single-writer model now matches reality exactly | sanitizer runs on every channel inbound |
| 10 (MC governance) | ✅ unchanged | Mission Control gains `/notify` endpoint to reach Milo |
| 11 (deployment topology) | ⚠️ amended — Hermes goes host-CLI → host-daemon | this doc supersedes the relevant table in PHASE_11 |
| 12 (observability) | ⚠️ amended — daily health report now probes Milo daemon | `daily-health-report.sh` updated |

### 13.5 Updated runtime topology

```
                                ┌──────────────────────────────┐
   John ◄─────────► Telegram ───┤                              │
   (any device)    Discord ─────┤  Milo daemon                 │
                   Hermes CLI ──┤  hermes-daemon/              │
                   MC /notify ──┤  127.0.0.1:18790 (LaunchAgent)│
                                └─────────────┬────────────────┘
                                              │  classify + sanitize
                                              ▼
                                  delegate_to_elon.sh (bridge)
                                              │
                                              ▼
                                  OpenClaw gateway (Elon)
                                  127.0.0.1:18789 (LaunchAgent)
                                              │
                                              ▼
                                  Specialists (cron dispatch, DEC-006)
                                  sagan / neo / kat / zuck / sentinel /
                                  cortana / cornelius

   Mission Control ◄────────────► OrbStack (5 containers, unchanged)
```

## Verification gates (Phase 13 PASS criteria)

1. `uv run hermes chat` → "What's your name and model?" → reports **Milo** on `minimax-m2.7:cloud`.
2. Gateway `main` agent reports **Elon**, model `openai-codex/gpt-5.5`. Companion App not running.
3. Telegram message → Milo daemon receives, replies in Telegram. (`hermes-daemon` log shows the inbound, Milo CLI subprocess runs, Telegram `sendMessage` returns 200.)
4. Discord message (with bot @-mention in allowlisted guild) → Milo daemon receives, replies in Discord channel.
5. End-to-end multi-step task: Telegram → Milo → bridge → Elon → Neo → result returns to Milo → Milo posts in Telegram.
6. MC Approvals board approval resolved → MC POSTs to `/notify` → daemon logs receipt.
7. Daily health report (08:00 CT next run) lists Milo daemon as ✅.
8. Reboot Mac Mini → LaunchAgent brings Milo daemon up within 60s (verify via `launchctl list | grep openhermes.milo` and `curl 127.0.0.1:18790/health`).

## Hermes CLI flags (verified empirically against installed version)

`milo_bridge.py` invokes:

```
uv run --project ~/repos/hermes-agent hermes chat \
   -Q                              # quiet/programmatic mode
   --provider ollama-cloud         # explicit; `provider: auto` resolves to OpenRouter which does not stock minimax-m2.7
   -m minimax-m2.7:cloud           # model id WITHOUT `ollama/` prefix (Hermes-style, not OpenClaw-style)
   --source <telegram|discord|api> # session source tag
   -q <sanitized text>             # single non-interactive query
```

Two gotchas surfaced during Phase 13 verification:

1. **Hermes config had `model.default: ollama/minimax-m2.7:cloud`** (OpenClaw-style ID). For Hermes' `ollama-cloud` provider the ID must be `minimax-m2.7:cloud` — no provider prefix. Fixed in `~/.hermes/config.yaml`.
2. **`provider: auto` resolves to OpenRouter** under `minimax-m2.7:cloud` — which has no such model and returns HTTP 400/402. The daemon passes `--provider ollama-cloud` explicitly to bypass auto-resolution.

Smoke-test result (2026-04-27):
```
$ uv run hermes chat -Q --provider ollama-cloud -m minimax-m2.7:cloud -q "State your name and model"
session_id: 20260427_121528_61aaa6
name=Milo model=minimax-m2.7:cloud
```

## Known follow-ons (Phase 14+)

1. **Per-user session continuity** — Phase 13 v1 spawns a fresh Hermes session per turn. Use `--continue {source}-{user_id}` once we verify Hermes session-name semantics handle "create-if-missing" gracefully (currently `--continue NAME` requires the session to pre-exist).
2. **`/notify` → in-session injection** — currently logs and 200s. Phase 14 should route the signal into Milo's active session as a system message so Milo can decide whether to surface it to John in the appropriate channel.
3. **Telegram + Discord credentials cleanup** — tokens still present (disabled) in `openclaw.json`. After 1 week of stable daemon operation, remove from openclaw.json entirely.
4. **Companion App repoint vs. uninstall** — defer. Either point it at the Milo daemon or remove it; current state (installed but not used) is acceptable.
5. **Hermes SDK over subprocess** — current per-turn `uv run hermes chat` overhead is ~1s warmup. If channel latency matters, switch to a long-running Hermes worker (Python SDK `AIAgent.chat()`) instead of subprocess-per-turn.
6. **Perplexity Sagan payload bug (DEC-006)** — still open upstream.
