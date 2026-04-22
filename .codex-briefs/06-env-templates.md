# Codex Brief #6 — `.env.example` + component env templates

**Target files:**
- `$OPENHERMES_ROOT/.env.example` (root)
- `$OPENHERMES_ROOT/deploy/env/milo.env.example`
- `$OPENHERMES_ROOT/deploy/env/elon.env.example`

**Priority:** Phase 11 (deployment).

---

## Prompt (paste into Codex)

Produce three environment templates. Each is a `.env.example`-style file with placeholder values only — NEVER commit actual secrets. Include inline comments explaining provenance and purpose of each variable.

### File 1: Root `.env.example` (all variables documented)

Group by category with section-header comments. Variables required:

**Milo (Nous Hermes front door):**
- `OLLAMA_API_KEY` — from ollama.com → Account Settings → API Keys. Primary provider for `minimax-m2.7:cloud`.
- `NVIDIA_NIM_API_KEY` — nvapi-... from build.nvidia.com. Fallback provider for Milo.

**Elon (OpenClaw orchestrator on GPT-5.4):**
- `ZAI_CODING_PLAN_KEY` — from Z.ai dashboard → GLM Coding Plan → API Keys. Tier-3 fallback (Elon primary uses OAuth proxy, no key needed).

**Bridge authentication:**
- `OPENCLAW_GATEWAY_TOKEN` — generated in Phase 11. Used by Milo to call Elon via OpenAI-compatible endpoint.
- `MILO_MCP_TOKEN` — generated in Phase 8. Used by Elon to call Milo's MCP tools.
- `OPENHERMES_EDGE_TOKEN` — generated in Phase 11. Caddy reverse proxy bearer-token auth.

**Per-agent write credentials (Phase 10 attribution):**
- `ZUCK_TWITTER_TOKEN` — Zuck's dedicated Twitter/X API bearer.
- `ZUCK_LINKEDIN_TOKEN` — Zuck's LinkedIn API token.
- `MILO_GMAIL_TOKEN` — Milo's Gmail OAuth token for email send.
- `MILO_SLACK_TOKEN` — Milo's Slack bot token for DM send.

**Observability (optional):**
- `SIEM_ENDPOINT` — if set, log-collector forwards NDJSON. Leave blank for local-only logging.

**Deployment (Phase 11):**
- `OPENHERMES_DOMAIN` — public domain for Caddy auto-HTTPS. Placeholder: `openhermes.example.com`.

### File 2: `deploy/env/milo.env.example`

Subset relevant to the Milo container ONLY:
- `OLLAMA_API_KEY`
- `NVIDIA_NIM_API_KEY`
- `OPENCLAW_GATEWAY_TOKEN` (to call Elon)
- `MILO_GMAIL_TOKEN`, `MILO_SLACK_TOKEN`
- `SIEM_ENDPOINT` (optional)

### File 3: `deploy/env/elon.env.example`

Subset relevant to the Elon container ONLY:
- `ZAI_CODING_PLAN_KEY` (tier-3 fallback)
- `MILO_MCP_TOKEN` (to call Milo)
- `ZUCK_TWITTER_TOKEN`, `ZUCK_LINKEDIN_TOKEN` (per-agent attribution when Elon dispatches Zuck)
- `SIEM_ENDPOINT` (optional)

### Constraints

- No secret values anywhere — only placeholder text like `<paste-key-here>` or `""`
- Each variable has a one-line comment explaining source + purpose
- Section headers as `# === Category Name ===`
- At the top of each file, include a 3-line header:
  1. What this file is for
  2. That it's a TEMPLATE, not to be used directly
  3. How to create the real file (`cp .env.example .env` and fill in)

---

## Acceptance criteria

- All three files parse with `dotenv-linter` (or `set -a; source <file>` cleanly)
- No real secrets — verified with `gitleaks detect --no-git`
- Variable names match exactly what's referenced elsewhere in OpenHermes (docker-compose.yml, config YAMLs)
- Comments are accurate — provenance is correct (e.g., NVIDIA NIM keys really are `nvapi-...` prefixed)
