# Codex Brief #9 — `LICENSE` + `README.md` scaffold

**Target files:**
- `$OPENHERMES_ROOT/LICENSE`
- `$OPENHERMES_ROOT/README.md`
- `$OPENHERMES_ROOT/SECURITY.md` (placeholder)

**Priority:** Blocks Phase 1 (public repo creation).

---

## Prompt (paste into Codex)

Produce three files for the public OpenHermes repo.

### File 1: `LICENSE`

Full standard MIT License text. Copyright line: `Copyright (c) 2026 MiloTheAssistant`.

### File 2: `README.md`

Public-facing. Explain the OpenHermes architecture at a high level, without revealing operational specifics or infrastructure details.

**Required sections:**

1. **Title + one-sentence mission statement**
   > OpenHermes is the integration layer between a conversational front-door agent (Nous Hermes) and an orchestration core (OpenClaw), with governance via Mission Control.

2. **What this is**
   - Two-layer multi-agent architecture
   - Name the three top-level agents (Milo / Elon / Zuck) with 1-line roles each
   - List the six specialists at a glance (Sagan, Neo, Kat, Sentinel, Cortana, Cornelius) with one-word role descriptors
   - No implementation details, no model names, no infrastructure specifics

3. **Architecture diagram**
   - ASCII art or Mermaid block showing:
     - User → Milo → (classifier) → Elon → {specialists} → Zuck (for publishing)
     - Mission Control as the governance gate
   - Don't label specific models, hostnames, or ports

4. **What's in this repository**
   - Reference configs (sanitized)
   - Bridge schemas
   - Governance policy templates
   - Runbooks and architecture docs
   - Build plan (`PLAN.md`)

5. **What's NOT in this repository**
   - Secrets, API keys, OAuth credentials (never committed)
   - Live memory or user data
   - Audit trails or session transcripts
   - Internal infrastructure identifiers (hostnames, IPs, usernames)

6. **Project status**
   > This repository is a reference implementation and coordination space. The system is being built in phases; see `PLAN.md` for current progress. Pull requests are not accepted during the build phase.

7. **Security**
   > If you discover a security issue, please see `SECURITY.md` for responsible disclosure.

8. **License**
   > MIT. See `LICENSE`.

**Tone:** professional, technical, concise. No marketing language. No emoji. No badges.

**Length:** ~150-250 lines. Scannable headings.

### File 3: `SECURITY.md`

Basic responsible-disclosure policy:

- How to report: encrypted email to `security@<placeholder-domain>` (user will replace)
- What's in scope: this repository's code and configs
- What's NOT in scope: third-party components (Nous Hermes, OpenClaw, Mission Control) — report to their upstream maintainers
- Response SLA: acknowledge within 48h, remediate within 30 days (or explain)
- Hall of fame: disclose reporter after remediation (with permission)

---

## Acceptance criteria

- `LICENSE` is the canonical MIT License text — no deviations
- `README.md` reveals architecture at a conceptual level but NO operational specifics (no model names visible to an attacker doing reconnaissance)
- `SECURITY.md` has all required sections
- No hardcoded email addresses, no real URLs — use placeholders the user can fill in
- Markdown lint-clean (no broken tables, no malformed links)
- Reading the README, a stranger understands "this is a multi-agent orchestration system" but gains nothing useful for attack planning
