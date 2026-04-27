# hermes-daemon — Milo's front-door HTTP service

> **Phase 13.** The Nous Hermes Agent framework runs as Milo, John's executive
> assistant. Hermes is a CLI by default; this daemon wraps it in a small
> long-running HTTP service so external channels (Telegram, Discord, Mission
> Control) can reach Milo without going through OpenClaw.

## Architecture

```
  Telegram (long-poll) ──┐
  Discord  (websocket) ──┼──► Milo daemon  (FastAPI, 127.0.0.1:18790)
  Mission Control       ──┤              │
  (HTTP POST)            └──┐            │  classify → sanitize → milo_bridge
  Terminal (uv run hermes chat) ─────────┤
                                          ▼
                                   Hermes Agent (Milo persona, ~/.hermes/SOUL.md)
                                          │
                                  delegates to ▼
                                  OpenClaw gateway (Elon, 127.0.0.1:18789)
                                          │
                                          ▼
                                  Specialists (cron dispatch, DEC-006)
```

## Endpoints

| Method | Path | Purpose |
|---|---|---|
| `GET` | `/health` | Liveness probe — used by `daily-health-report.sh` |
| `POST` | `/chat` | Send a message to Milo; returns Milo's reply. Body: `{user_id, source, text}` |
| `POST` | `/notify` | Mission Control approval-resolution sink. Body: `{kind, payload}` |

## Files

- `main.py` — FastAPI app + lifespan (starts Telegram + Discord workers)
- `milo_bridge.py` — invokes Milo (Hermes Agent) and returns the reply
- `telegram_poller.py` — long-polling worker
- `discord_bot.py` — websocket bot worker
- `settings.py` — env-var loader (reads `~/.openhermes/milo-daemon.env`)
- `requirements.txt` — pinned deps

## Running

### First-time install

```bash
cd ~/repos/OpenHermes/hermes-daemon
uv venv
uv pip install -r requirements.txt
```

### Foreground (for first-run verification — watch the log)

```bash
cd ~/repos/OpenHermes/hermes-daemon
uv run uvicorn main:app --host 127.0.0.1 --port 18790
```

In another terminal:
```bash
# health check
curl -s http://127.0.0.1:18790/health | python3 -m json.tool

# direct chat probe (no Telegram/Discord needed)
curl -s -X POST http://127.0.0.1:18790/chat \
  -H 'Content-Type: application/json' \
  -d '{"user_id":"verify","source":"api","text":"State your name and model"}' \
  | python3 -m json.tool
```

### LaunchAgent (background, persistent)

```bash
cp ~/repos/OpenHermes/hermes-daemon/com.openhermes.milo.plist ~/Library/LaunchAgents/
launchctl bootstrap gui/$UID ~/Library/LaunchAgents/com.openhermes.milo.plist
launchctl enable gui/$UID/com.openhermes.milo
launchctl kickstart -k gui/$UID/com.openhermes.milo

# verify
launchctl list | grep openhermes.milo
curl -s http://127.0.0.1:18790/health
tail -f ~/.openhermes/logs/milo-daemon.out
```

To stop / unload:
```bash
launchctl bootout gui/$UID/com.openhermes.milo
```

## Security posture

- Loopback bind only (`127.0.0.1`). No public exposure.
- Channel allowlists enforced at the daemon, not at Telegram/Discord.
- `~/.openhermes/milo-daemon.env` is mode `0600`, owner-only.
- Sanitizer (`bridge/scripts/sanitize-memory.py`) runs on every inbound message
  before it reaches Milo's memory write path.
