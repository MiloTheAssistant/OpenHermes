# Memory Contract

> **Status:** Active contract. Enforced by pre-commit hook and sanitizer.
> **Owner:** Milo (all memory writes), Cortana (telemetry only, separate path).

---

## Single-writer rule

**Milo is the sole writer** of the following files in `workspace/memory/`:

- `MEMORY.md` — Milo's long-horizon memory (durable facts, projects, preferences)
- `USER.md` — facts about John (name, timezone, pronouns, channel preferences)

No other agent — not Elon, not the specialists, not Zuck — writes these files. They can **read** via MCP (where wired) but never modify.

**Cortana writes** `workspace/memory/TELEMETRY.md` only. This is a separate file on a separate path and is deliberately segregated so Cortana's telemetry writes (usage counts, cost summaries, event logs) never collide with Milo's memory semantics.

## Why single-writer

Concurrent writes by multiple agents produced two classes of bug in prior OpenClaw work:
- Race conditions between Milo's compaction and specialist-triggered memory writes (content lost in merge)
- Persona drift from specialists writing their own perspective into MEMORY (Milo's voice diluted)

Single-writer eliminates both. Specialists return structured envelopes; Milo decides what (if anything) to record.

## What goes into memory

Milo writes memory entries when:
- John shares a durable fact about himself, his preferences, his projects
- A decision is made that should persist across sessions (e.g., DEC-NNN entries)
- An infrastructure change or model matrix update is committed
- A new channel, account, or integration is provisioned

Milo does **not** write to memory for:
- Transient task state (that's session-scoped)
- Specialist outputs (those go to artifacts, not memory)
- Failed dispatches (no value in persisting what didn't work, per DEC-005 discipline)
- PII from external inbound messages without explicit user instruction

## Prompt-injection sanitization

Every piece of user-originated content (chat messages, inbound emails, document uploads, scraped web content) passes through `bridge/scripts/sanitize-memory.py` before Milo can write it to memory.

The sanitizer:
- Strips known prompt-injection patterns ("ignore previous instructions," "you are now...", "system:", etc.)
- Detects embedded instruction blocks in Markdown, XML, HTML
- Flags suspicious content for Sentinel review instead of blind-writing it
- Preserves an **untrusted-origin** marker on anything that came from an external source

Content that trips the sanitizer's block rules is NOT auto-written to memory. It is returned to Milo with a `sanitizer_verdict: blocked` field. Milo may re-prompt John for explicit "yes, write this to memory" confirmation before bypassing.

## Nightly compaction

Nous Hermes runs a scheduled compaction pass on `workspace/memory/MEMORY.md` nightly at 02:00 local (configurable via `memory.compaction_cron` in `~/.hermes/config.yaml`).

The compaction pass:
- Promotes frequently-accessed short-term recalls into canonical long-term entries
- Deduplicates redundant entries (same fact restated)
- Archives stale entries (not accessed for 30+ days) to `workspace/memory/archive/`
- Preserves `USER.md` verbatim (user profile is never compacted — human-authored)

Cortana's `TELEMETRY.md` has its own separate rotation logic managed by the telemetry subsystem and is not touched by memory compaction.

## Enforcement

### Pre-commit hook

`.githooks/pre-commit-memory` rejects commits that modify `workspace/memory/MEMORY.md` or `USER.md` unless the committing process is running as Milo (checked via parent process env or explicit `MILO_WRITER_TOKEN` presence).

In practice, memory files are **not tracked in the repo** (gitignored per public-repo hygiene). The hook applies to any local clone where someone might attempt to check-in memory state. It's defense-in-depth.

### File integrity monitoring

`SOUL.md`, `AGENTS.md` (reference), and `MEMORY.md` are monitored for unexpected changes. Any diff between sessions is logged with timestamp and process origin. Unauthorized edits trigger a Sentinel alert to Milo.

### Violation response

If a non-Milo process attempts to write to `MEMORY.md` or `USER.md`:
1. Write is rejected
2. Event is logged to `governance/audit/memory-violations.jsonl` (append-only)
3. Sentinel is notified
4. Milo surfaces the violation to John on next interaction

## Rollback

Every memory write by Milo is also a git commit inside the `workspace/memory/` subtree. Rollbacks are `git revert` in that subtree. The subtree is git-tracked locally but gitignored from the public OpenHermes repo.

## Audit trail

`governance/audit/memory-writes.jsonl` records every successful memory write:
- Timestamp (ISO 8601 UTC)
- Writer process (should always be Milo)
- File + line ranges touched
- Brief content description (no sensitive payload)
- Git commit SHA in the workspace subtree

Append-only. Rotated weekly. Weekly SHA-256 checksum committed to repo for tamper-evidence.
