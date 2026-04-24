# Secrets Runbook

This runbook covers what to do when automated secret scanning finds exposed or suspected secret material in the repository.

## Immediate Response

1. Rotate the affected credential or secret.
2. Remove the secret from the working tree.
3. Rewrite repository history if the secret was committed.
4. Force-push the cleaned history only after verifying the rewrite.

## History Cleanup

Use `git filter-repo` or an equivalent history-rewrite tool to purge the material from all affected commits and refs.

After the rewrite:

1. Re-run local scans (`gitleaks`, `detect-secrets`, and pre-commit hooks).
2. Confirm the secret no longer appears in the GitHub Actions scan results.
3. Force-push the cleaned branch or the rewritten default branch as appropriate.

## Baseline Audits

Only update `.secrets.baseline` for verified false positives.

Do not use the baseline as a way to suppress real credentials.

When auditing a false positive:

1. Confirm the value is non-sensitive and intentionally present.
2. Record why it is safe to suppress.
3. Update the baseline in the same change that documents the reasoning.

## Scope

This runbook applies to repository contents, committed history, generated artifacts, and CI findings related to OpenHermes.
