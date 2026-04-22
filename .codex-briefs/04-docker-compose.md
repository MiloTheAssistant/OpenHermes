# Codex Brief #4 — `docker-compose.yml` + `Caddyfile`

**Target files:**
- `$OPENHERMES_ROOT/deploy/docker/docker-compose.yml`
- `$OPENHERMES_ROOT/deploy/docker/Caddyfile`

**Priority:** Phase 11 (OrbStack deployment).

---

## Prompt (paste into Codex)

Produce an OrbStack-compatible (macOS) `docker-compose.yml` with 3 services plus 2 networks, and a matching `Caddyfile`.

### Networks

- `openhermes_internal` — bridge driver, `internal: true` (no outbound internet for traffic between Milo and Elon)
- `openhermes_edge` — bridge driver (for external ingress via Caddy)

### Service 1: `milo`

- `build.context: ../../../hermes-agent`
- `container_name: milo`
- Networks: `openhermes_internal` + `openhermes_edge`
- Volumes:
  - `../../workspace:/workspace:rw` (workspace is writable for Milo — single-writer owner)
  - `../env/milo.env:/etc/milo/env:ro`
- Ports: `127.0.0.1:8787:8787` (MCP/SSE, loopback only — external access goes through Caddy)
- `restart: unless-stopped`
- `depends_on: elon` (so Elon is up before Milo tries to delegate)

### Service 2: `elon`

- `build.context: ../../../openclaw-master`
- `container_name: elon`
- Networks: `openhermes_internal` only (no edge exposure — Elon is internal)
- Volumes:
  - `../../workspace:/workspace:ro` (Elon reads workspace, cannot write — memory contract)
  - `../env/elon.env:/etc/elon/env:ro`
- Ports: `127.0.0.1:18789:18789` (OpenClaw gateway, loopback only)
- `restart: unless-stopped`

### Service 3: `reverse_proxy`

- `image: caddy:2`
- `container_name: openhermes_proxy`
- Networks: `openhermes_edge` only
- Ports: `443:443` (public ingress)
- Volumes:
  - `./Caddyfile:/etc/caddy/Caddyfile:ro`
  - `caddy_data:/data` (for Caddy's auto-HTTPS cert storage)
  - `caddy_config:/config`
- `restart: unless-stopped`

### Top-level volumes

- `caddy_data`
- `caddy_config`

---

## Caddyfile

- Automatic HTTPS via Let's Encrypt on a placeholder domain (`{$OPENHERMES_DOMAIN}` — provisioned via env)
- Authenticated reverse proxy:
  - Route `/chat/*` to `milo:8787`
  - Require header `Authorization: Bearer {env.OPENHERMES_EDGE_TOKEN}` — reject all requests without it (return 401)
  - Reject all other paths with 404
- Enable access logs in JSON format
- No default `respond` block — must explicitly reject unknown paths

---

## Acceptance criteria

- `docker compose -f deploy/docker/docker-compose.yml config` parses without errors (use OrbStack's docker CLI)
- Services come up in order: elon → milo → reverse_proxy
- Elon cannot reach the internet from inside `openhermes_internal` (because `internal: true`)
- Caddy rejects requests without the auth header
- Caddy serves `/chat/*` via milo:8787 after auth
- All compose entries use env var references for anything environment-specific (domain, token, etc.) — no hardcoded values
