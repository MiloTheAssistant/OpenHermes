# Codex Brief #2 — `.pre-commit-config.yaml` + `.secrets.baseline`

**Target files:**
- `$OPENHERMES_ROOT/.pre-commit-config.yaml`
- `$OPENHERMES_ROOT/.secrets.baseline`

**Priority:** Blocks Phase 1 (public repo creation).

---

## Prompt (paste into Codex)

Configure pre-commit hooks for a public GitHub repo (`OpenHermes`). Required hooks:

### 1. gitleaks v8.21.2

Detect committed secrets.

### 2. detect-secrets v1.5.0

With baseline support. Exclude `package-lock.json` and the `.secrets.baseline` file itself.

### 3. pre-commit-hooks v5.0.0

Specifically:
- `check-added-large-files` with `--maxkb=1024`
- `check-merge-conflict`
- `detect-private-key`
- `check-yaml`
- `check-json`
- `end-of-file-fixer`
- `trailing-whitespace`

### Stages

Install hooks at BOTH `pre-commit` AND `pre-push` stages (defense in depth).

---

## Deliverables

### File 1: `.pre-commit-config.yaml`

Complete, valid YAML. Include a top-of-file comment explaining the file's purpose and install command.

### File 2: `.secrets.baseline` (seed)

Minimal empty seed suitable for `detect-secrets scan --baseline .secrets.baseline`. Initial state: zero findings, zero filters applied beyond the defaults for a Python/Node/YAML project.

### File 3: Install commands (as comment block or separate markdown)

Provide the exact commands to:
1. Install `pre-commit` via pip
2. Install the hooks into `.git/hooks/`
3. Run against all files initially (`pre-commit run --all-files`)
4. Confirm the baseline is valid

---

## Acceptance criteria

- `pre-commit run --all-files` exits 0 on a clean scaffold
- gitleaks runs and reports nothing on a scaffold with no secrets
- detect-secrets runs against baseline and reports no new findings
- pre-push stage is registered (visible in `.git/hooks/pre-push`)
