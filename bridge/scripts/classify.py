"""Deterministic governance-class classifier for OpenHermes handoffs.

The classifier is pure-rule, not LLM-driven. Milo calls this on every request
to decide the routing lane. Output maps to one of four governance classes:

  info          — internal answer, no side effects, Milo handles directly
  action        — internal side effects (file writes, local API calls,
                  internal messages), Milo → Elon → specialist
  publish       — externally visible (public social, email to external,
                  blog posts), Milo → Elon → Zuck → Mission Control approval
  irreversible  — infra changes, secret rotations, deletions, financial
                  actions, Milo → Elon → Sentinel → MC approval + user confirm

The classifier receives a structured task description (not free text) and
returns the class + the suggested routing target. Milo is expected to respect
the classifier's decision — it cannot bypass an `irreversible` class just
because the user asked nicely.

Usage:
    python3 classify.py <<'EOF'
    {
      "summary": "Post a tweet about the new product launch",
      "side_effects": ["post_social"],
      "targets": ["twitter"],
      "tools_requested": ["zuck.publish"],
      "risk_signals": {}
    }
    EOF

Exit codes: 0 success, 1 on invalid input or classifier error.
"""
from __future__ import annotations

import json
import sys
from typing import Any

# --- Side effects that trigger each class --------------------------------

_IRREVERSIBLE_SIDE_EFFECTS = frozenset({
    "infra_change",
    "secret_rotation",
    "credential_revoke",
    "financial_transaction",
    "data_deletion",
    "repo_delete",
    "database_drop",
    "dns_change",
    "account_delete",
})

_PUBLISH_SIDE_EFFECTS = frozenset({
    "post_social",
    "post_x",
    "post_linkedin",
    "post_threads",
    "post_instagram",
    "post_blog",
    "send_external_email",
    "newsletter_send",
})

_ACTION_SIDE_EFFECTS = frozenset({
    "file_write",
    "file_edit",
    "file_delete_local",
    "internal_api_call",
    "send_internal_message",
    "send_discord_dm",
    "send_telegram_dm",
    "send_slack_dm",
    "create_task",
    "schedule_cron",
    "config_patch",
    "memory_write",
    "git_commit",
    "git_branch",
})

# --- Tool namespaces that imply a class ---------------------------------

_IRREVERSIBLE_TOOLS = frozenset({
    "exec",  # shell commands can do anything
    "sentinel.approve_infra",
    "cortana.purge",
})

_PUBLISH_TOOLS = frozenset({
    "zuck.publish",
    "zuck.schedule",
    "hermes.send_external",
})

# --- Target surfaces that imply external reach ---------------------------

_EXTERNAL_TARGETS = frozenset({
    "twitter", "x", "linkedin", "threads", "instagram",
    "blog", "public_newsletter", "external_email",
})


def classify(task: dict[str, Any]) -> dict[str, Any]:
    """Classify a handoff task. Pure function, no I/O.

    Args:
        task: dict with (all optional, but at minimum `summary`):
            - summary: str — short human description of the request
            - side_effects: list[str] — declared side-effect tags
            - targets: list[str] — target surfaces/platforms
            - tools_requested: list[str] — tool names/namespaces the
              request needs
            - risk_signals: dict — e.g. {"amount": 100, "recipient": ...}

    Returns:
        dict with:
            - governance_class: "info" | "action" | "publish" | "irreversible"
            - reason: str — brief rule rationale
            - required_route: "milo" | "milo->elon" |
              "milo->elon->zuck->mc" | "milo->elon->sentinel->mc+user"
            - requires_halt: bool — true for irreversible
            - requires_mc_approval: bool — true for publish + irreversible
    """
    side = {s.lower() for s in (task.get("side_effects") or [])}
    targets = {t.lower() for t in (task.get("targets") or [])}
    tools = {t.lower() for t in (task.get("tools_requested") or [])}

    # ---- IRREVERSIBLE — highest precedence ---------------------------
    if side & _IRREVERSIBLE_SIDE_EFFECTS:
        matched = sorted(side & _IRREVERSIBLE_SIDE_EFFECTS)
        return {
            "governance_class": "irreversible",
            "reason": f"irreversible side effects: {matched}",
            "required_route": "milo->elon->sentinel->mc+user",
            "requires_halt": True,
            "requires_mc_approval": True,
        }
    if tools & _IRREVERSIBLE_TOOLS:
        matched = sorted(tools & _IRREVERSIBLE_TOOLS)
        return {
            "governance_class": "irreversible",
            "reason": f"irreversible tool requested: {matched}",
            "required_route": "milo->elon->sentinel->mc+user",
            "requires_halt": True,
            "requires_mc_approval": True,
        }

    # ---- PUBLISH ------------------------------------------------------
    if side & _PUBLISH_SIDE_EFFECTS:
        matched = sorted(side & _PUBLISH_SIDE_EFFECTS)
        return {
            "governance_class": "publish",
            "reason": f"publish side effects: {matched}",
            "required_route": "milo->elon->zuck->mc",
            "requires_halt": False,
            "requires_mc_approval": True,
        }
    if tools & _PUBLISH_TOOLS:
        matched = sorted(tools & _PUBLISH_TOOLS)
        return {
            "governance_class": "publish",
            "reason": f"publish tool requested: {matched}",
            "required_route": "milo->elon->zuck->mc",
            "requires_halt": False,
            "requires_mc_approval": True,
        }
    if targets & _EXTERNAL_TARGETS:
        matched = sorted(targets & _EXTERNAL_TARGETS)
        return {
            "governance_class": "publish",
            "reason": f"external target surface: {matched}",
            "required_route": "milo->elon->zuck->mc",
            "requires_halt": False,
            "requires_mc_approval": True,
        }

    # ---- ACTION -------------------------------------------------------
    if side & _ACTION_SIDE_EFFECTS:
        matched = sorted(side & _ACTION_SIDE_EFFECTS)
        return {
            "governance_class": "action",
            "reason": f"action side effects: {matched}",
            "required_route": "milo->elon",
            "requires_halt": False,
            "requires_mc_approval": False,
        }
    if tools and not all(t.startswith(("milo.", "memory_", "read")) for t in tools):
        # Any tool not in the read-only milo/memory namespace → action
        external_tools = sorted(t for t in tools
                                 if not t.startswith(("milo.", "memory_", "read")))
        return {
            "governance_class": "action",
            "reason": f"non-read-only tools requested: {external_tools}",
            "required_route": "milo->elon",
            "requires_halt": False,
            "requires_mc_approval": False,
        }

    # ---- INFO (default) ----------------------------------------------
    return {
        "governance_class": "info",
        "reason": "no side effects, no external targets, read-only or no tools",
        "required_route": "milo",
        "requires_halt": False,
        "requires_mc_approval": False,
    }


def _load_task(argv: list[str]) -> dict[str, Any]:
    if len(argv) > 1:
        raise SystemExit("usage: classify.py [task.json]   (or pipe JSON to stdin)")
    payload = (
        open(argv[0], encoding="utf-8").read() if len(argv) == 1 else sys.stdin.read()
    )
    if not payload.strip():
        raise SystemExit("no JSON task provided")
    data = json.loads(payload)
    if not isinstance(data, dict):
        raise SystemExit("task JSON must be an object")
    return data


def main() -> int:
    try:
        task = _load_task(sys.argv[1:])
        result = classify(task)
    except json.JSONDecodeError as exc:
        print(f"invalid JSON: {exc}", file=sys.stderr)
        return 1
    except SystemExit as exc:
        print(str(exc), file=sys.stderr)
        return 1

    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
