# Codex Briefs for OpenHermes Build

Parallel workstreams delegated to Codex (GPT-5.4) while Claude Code executes the integration-heavy phases.

## How to use these briefs

1. Open the brief file you want to work.
2. Copy the "Prompt (paste into Codex)" section.
3. Paste it into your Codex session (or into the body of the corresponding GitHub issue if Codex is wired to pick it up).
4. Review Codex's output against the "Acceptance criteria" at the bottom of the brief.
5. Save output to the indicated "Target file" path(s).
6. Ping Claude Code: "Codex Brief #N is ready" — Claude will integrate, test, and mark the corresponding todo done.

## Order to run (recommended)

**🔥 Fire now (blocks Phase 1 — public repo creation):**
- `01-gitignore.md`
- `02-pre-commit.md`
- `09-readme-license.md`

**🔥 Fire second (blocks Phase 2 — migration):**
- `10-migration-script.md`

**Fire when convenient (parallelizable, non-blocking):**
- `03-handoff-schema.md` — Phase 8
- `04-docker-compose.md` — Phase 11
- `05-log-collector.md` — Phase 12
- `06-env-templates.md` — Phase 11
- `07-launchd-oauth.md` — Phase 5
- `08-secret-scan-workflow.md` — Phase 1 (non-blocking — belt-and-suspenders)

## Convention

Each brief has five sections:

1. **Target file(s)** — where the output goes
2. **Priority** — which phase it blocks
3. **Prompt** — the actual text to paste into Codex
4. **Deliverables** (if multiple files)
5. **Acceptance criteria** — what "done" looks like

Claude Code will not proceed past Gate 1 (public repo creation) until briefs #1, #2, #9 are integrated and scanners are clean. Claude Code will not proceed past Gate 2 (migration) until brief #10 is integrated.

## Track progress

Match each brief to a GitHub issue by number. When Codex completes a brief and the output passes Claude's acceptance check, Claude will close the issue with a reference to the integrating commit.
