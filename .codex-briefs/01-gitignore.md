# Codex Brief #1 — Hardened `.gitignore`

**Target file:** `$OPENHERMES_ROOT/.gitignore`

**Priority:** Blocks Phase 1 (public repo creation).

---

## Prompt (paste into Codex)

Produce a hardened `.gitignore` for a PUBLIC GitHub repo named `OpenHermes`. Repo contents: Python (uv/.venv), Node (node_modules), Docker/OrbStack, macOS dev environment.

Must aggressively block:

- **All `.env` variants** (allow `.env.example` only): `.env`, `.env.*`, but `!.env.example`
- **Private keys/certs:** `*.pem`, `*.key`, `*.p12`, `*.pfx`, `*.crt`
- **Common token/apikey filename patterns:** `*token*`, `*apikey*`, `*api_key*`, `*api-key*`, `*.secret`, `id_rsa`, `id_ed25519`, `id_dsa`, `id_ecdsa`, `known_hosts`
- **OAuth state dirs:** `.openai-oauth/`, `.hermes/auth/`, `.hermes/session/`
- **Cloud credentials:** `.aws/`, `.gcp/`, `.azure/`, `gcp-key.json`, `aws-credentials`, `service-account*.json`
- **Secrets containers:** `secrets/`, `credentials/`, `.secrets`, `.credentials`
- **Runtime state/PII:** `workspace/memory/*.md` (but `!workspace/memory/.gitkeep`, `!workspace/memory/README.md`), `workspace/memory/archive/`, `workspace/telemetry/`, `governance/audit/*.jsonl`, `logs/`, `*.log`, `*.pid`
- **Build artifacts:** `node_modules/`, `.venv/`, `venv/`, `__pycache__/`, `*.pyc`, `.pytest_cache/`, `.mypy_cache/`, `.ruff_cache/`, `dist/`, `build/`, `*.egg-info/`
- **Docker/OrbStack local state:** `.docker-compose.override.yml`, `docker-compose.override.yml`, `.orbstack/`
- **IDE/editor config (may leak paths/tokens):** `.vscode/settings.json`, `.idea/`, `.cursor/`, `*.swp`, `*.swo`, `*~`
- **OS noise:** `.DS_Store`, `Thumbs.db`, `desktop.ini`
- **Test/scan outputs:** `.secrets.baseline.new`, `gitleaks-report.*`, `bandit-service.*`, `coverage.*`, `htmlcov/`

Organize the file with section-header comments like `# === SECRETS — NEVER COMMIT ===`. Be exhaustive — public repo, zero tolerance for leakage.

---

## Acceptance criteria

- Running `git check-ignore -v <any-file-from-blocked-list>` returns a match
- `.env.example` is NOT ignored (the exception must work)
- `workspace/memory/.gitkeep` and `workspace/memory/README.md` are NOT ignored
- `.gitkeep` files in other scaffolded dirs are NOT ignored
