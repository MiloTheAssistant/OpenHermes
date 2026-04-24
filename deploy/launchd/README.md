# openai-oauth LaunchAgent

This directory contains the launchd LaunchAgent for the `openai-oauth` proxy that exposes an OpenAI-compatible endpoint at `http://127.0.0.1:10531/v1`.

The proxy must run as the logged-in user because it relies on the user's browser-authenticated ChatGPT or Codex session.

## Install

**IMPORTANT:** macOS `launchd` does not expand `~` or `$HOME` in plist paths. The committed plist uses `@HOME@` as a placeholder that MUST be substituted with the actual home directory at install time.

```bash
mkdir -p ~/Library/Logs/openhermes
mkdir -p ~/.openai-oauth

# Substitute @HOME@ placeholder → absolute home path during install
sed "s|@HOME@|$HOME|g" deploy/launchd/com.openhermes.openai-oauth.plist \
  > ~/Library/LaunchAgents/com.openhermes.openai-oauth.plist

# Validate the plist parses cleanly
plutil -lint ~/Library/LaunchAgents/com.openhermes.openai-oauth.plist

launchctl bootstrap gui/$(id -u) ~/Library/LaunchAgents/com.openhermes.openai-oauth.plist
launchctl enable gui/$(id -u)/com.openhermes.openai-oauth
```

## Uninstall

```bash
launchctl bootout gui/$(id -u)/com.openhermes.openai-oauth
rm ~/Library/LaunchAgents/com.openhermes.openai-oauth.plist
```

## Inspect

```bash
launchctl list | grep openhermes
tail -f ~/Library/Logs/openhermes/oauth-proxy.log
tail -f ~/Library/Logs/openhermes/oauth-proxy.err.log
```

## Troubleshooting

- Check `~/Library/Logs/openhermes/oauth-proxy.log` and `~/Library/Logs/openhermes/oauth-proxy.err.log` first.
- Verify the endpoint is live with `curl http://127.0.0.1:10531/v1/models`.
- If the proxy does not start after login, unload and bootstrap it again from `~/Library/LaunchAgents/`.
- If the session appears expired, stop the LaunchAgent, run `openai-oauth` manually once to trigger a fresh browser-based OAuth flow, confirm `curl http://127.0.0.1:10531/v1/models` works, then re-bootstrap the agent.

## Integration Notes

Elon uses this proxy as the primary provider endpoint for OpenAI-compatible model access.

The LaunchAgent keeps the local proxy available across logins and restarts it on crashes, while avoiding tight restart loops with a 30-second throttle interval.
