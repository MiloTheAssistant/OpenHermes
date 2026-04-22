# Codex Brief #7 — launchd plist for `openai-oauth` proxy

**Target file:** `$OPENHERMES_ROOT/deploy/launchd/com.openhermes.openai-oauth.plist`

**Priority:** Phase 5 (Elon on GPT-5.4 OAuth).

---

## Prompt (paste into Codex)

Produce a macOS launchd property list (plist) that supervises the `openai-oauth` Node.js process on the user's Mac mini. The proxy exposes an OpenAI-compatible endpoint at `http://127.0.0.1:10531/v1` backed by the user's ChatGPT/Codex session and is a critical dependency for Elon's primary model provider.

### Requirements

- **Label:** `com.openhermes.openai-oauth`
- **Runs at user login (LaunchAgent, not LaunchDaemon)** — the proxy requires the user's browser-logged-in ChatGPT session and must run under the user account
- **Program invocation:** `openai-oauth` (assumed on PATH after `npm install -g openai-oauth`)
- **Auto-restart on crash** (`KeepAlive` with `SuccessfulExit: false`) — restart ONLY on failure, not on clean exit
- **Throttle restarts** — if the proxy crashes repeatedly, back off to avoid tight loops (`ThrottleInterval: 30`)
- **Logs:**
  - stdout → `~/Library/Logs/openhermes/oauth-proxy.log`
  - stderr → `~/Library/Logs/openhermes/oauth-proxy.err.log`
  - Auto-create log directory (handled in install script, document it)
- **Environment:** inherit user session (do NOT set explicit env — the proxy needs the user's shell environment including any OAuth cache)
- **Working directory:** `~/.openai-oauth/` (create if missing)

### Plist format

Standard Apple plist DTD declaration, XML format. `<dict>` root keyed by launchd's documented keys (Label, ProgramArguments, KeepAlive with success-exit dict, ThrottleInterval, StandardOutPath, StandardErrorPath, WorkingDirectory, RunAtLoad).

### Install/uninstall comments at top of file

Include these as comment blocks (before the plist XML):

```
# INSTALL:
#   mkdir -p ~/Library/Logs/openhermes
#   mkdir -p ~/.openai-oauth
#   cp deploy/launchd/com.openhermes.openai-oauth.plist ~/Library/LaunchAgents/
#   launchctl bootstrap gui/$(id -u) ~/Library/LaunchAgents/com.openhermes.openai-oauth.plist
#   launchctl enable gui/$(id -u)/com.openhermes.openai-oauth
#
# UNINSTALL:
#   launchctl bootout gui/$(id -u)/com.openhermes.openai-oauth
#   rm ~/Library/LaunchAgents/com.openhermes.openai-oauth.plist
#
# INSPECT:
#   launchctl list | grep openhermes
#   tail -f ~/Library/Logs/openhermes/oauth-proxy.log
```

Note: XML comments (`<!-- -->`) don't work at the top of plist files reliably. Put the install instructions in a companion README at `deploy/launchd/README.md` instead, and reference it from a terse comment in the plist preamble.

### Companion README (`deploy/launchd/README.md`)

Full install/uninstall/inspect instructions above, plus:
- Troubleshooting tips (log paths, how to test the endpoint is live with `curl http://127.0.0.1:10531/v1/models`)
- How to force a one-time OAuth re-auth if the session expires
- How this integrates with Elon's provider config

---

## Acceptance criteria

- `plutil -lint com.openhermes.openai-oauth.plist` returns OK
- `launchctl bootstrap` with the plist succeeds on macOS 26+
- Proxy auto-restarts within 30s after `kill -9`
- Log files accumulate in `~/Library/Logs/openhermes/`
- No hardcoded username, no absolute user path in the plist (use `~` / environment expansion)
