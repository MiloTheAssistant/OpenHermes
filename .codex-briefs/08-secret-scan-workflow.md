# Codex Brief #8 — GitHub Actions workflow: secret scan

**Target file:** `$OPENHERMES_ROOT/.github/workflows/secret-scan.yml`

**Priority:** Phase 1 (belt-and-suspenders to local pre-commit hooks).

---

## Prompt (paste into Codex)

Produce a GitHub Actions workflow file (`.github/workflows/secret-scan.yml`) that runs secret scanning on every push and pull request for the `OpenHermes` public repo.

### Triggers

- `push` to `main`
- `pull_request` to `main`

### Jobs

**Job 1: `gitleaks`**

- Runner: `ubuntu-latest`
- Steps:
  1. `actions/checkout@v4` with `fetch-depth: 0` (full history — we scan the whole repo)
  2. Install gitleaks v8.21.2 (pinned version)
  3. Run `gitleaks detect --source . --verbose --redact --log-opts="--all"` against full history
  4. On failure, post a comment on the PR explaining:
     - What was detected (REDACTED — no actual secret values)
     - Remediation steps: rotate, purge history with `git filter-repo`, force-push
     - Link to `docs/governance/SECRETS.md` for the runbook
  5. Fail the job

**Job 2: `detect-secrets`**

- Runner: `ubuntu-latest`
- Steps:
  1. `actions/checkout@v4`
  2. Setup Python 3.11
  3. Install detect-secrets v1.5.0
  4. Run `detect-secrets scan --baseline .secrets.baseline` against working tree
  5. Compare output to committed baseline. If NEW findings appear (not already audited in `.secrets.baseline`), fail with a PR comment listing the new detections and instructing the author to either audit (mark as false positive) or remove the secret
  6. Fail the job if new findings exist

### PR comment implementation

Use `actions/github-script@v7` to post PR comments. Keep comments appendable, not duplicating — check if a previous comment from the workflow exists and edit rather than re-post.

### Concurrency

Use `concurrency.group: ${{ github.workflow }}-${{ github.ref }}` and `cancel-in-progress: true` to prevent stale runs.

### Permissions

- `contents: read`
- `pull-requests: write` (to post comments)

---

## Acceptance criteria

- Workflow file validates (`act --dry` or equivalent)
- Runs on PR and on push-to-main
- Both jobs fail if they detect anything new
- PR comments appear with redacted detection info (never leaking the secret itself)
- Uses pinned action versions (no `@main` or `@latest`)
- Concurrency handling prevents duplicate runs
