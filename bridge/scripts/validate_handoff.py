from __future__ import annotations

"""Validate OpenHermes handoff envelopes.

Sample valid envelope:
{
  "task_id": "01ARZ3NDEKTSV4RRFFQ69G5FAV",
  "origin_agent": "milo",
  "target_agent": "elon",
  "request_summary": "Route a research task to Sagan.",
  "governance_class": "info",
  "routing_profile": "research-default",
  "risk_level": "low",
  "requires_halt": false,
  "budget": {
    "max_tokens": 4000,
    "max_seconds": 120,
    "max_tool_calls": 6
  },
  "artifacts": [
    {
      "kind": "note",
      "body": "User asked for a concise market scan."
    }
  ],
  "status": "pending",
  "next_action": "Dispatch to the research specialist.",
  "audit": {
    "created_at": "2026-04-22T20:15:33Z",
    "created_by": "milo",
    "trace_id": "handoff-trace-001"
  }
}
"""

import json
import sys
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator


def _default_schema_path() -> Path:
    return Path(__file__).resolve().parent.parent / "schemas" / "handoff.schema.json"


def _format_error_path(error: Any) -> str:
    if not error.path:
        return "$"
    return "$." + ".".join(str(part) for part in error.path)


def validate_handoff(envelope: dict, schema_path: str = None) -> tuple[bool, list[str]]:
    """Validate an envelope dict against the schema.

    Returns (is_valid, errors_list). errors_list is empty on success.
    """

    schema_file = Path(schema_path) if schema_path else _default_schema_path()
    schema = json.loads(schema_file.read_text(encoding="utf-8"))
    validator = Draft202012Validator(schema)

    errors = []
    for error in sorted(validator.iter_errors(envelope), key=lambda item: list(item.path)):
        errors.append(f"{_format_error_path(error)}: {error.message}")
    return (len(errors) == 0, errors)


def _load_envelope(argv: list[str]) -> dict:
    if len(argv) > 1:
        raise SystemExit("usage: validate_handoff.py [envelope.json]")

    if len(argv) == 1:
        payload = Path(argv[0]).read_text(encoding="utf-8")
    else:
        payload = sys.stdin.read()

    if not payload.strip():
        raise SystemExit("no JSON envelope provided")

    data = json.loads(payload)
    if not isinstance(data, dict):
        raise SystemExit("envelope JSON must be an object")
    return data


def main() -> int:
    try:
        envelope = _load_envelope(sys.argv[1:])
        is_valid, errors = validate_handoff(envelope)
    except FileNotFoundError as exc:
        print(f"schema or envelope file not found: {exc}", file=sys.stderr)
        return 1
    except json.JSONDecodeError as exc:
        print(f"invalid JSON: {exc}", file=sys.stderr)
        return 1
    except SystemExit as exc:
        print(str(exc), file=sys.stderr)
        return 1

    if is_valid:
        print("VALID")
        return 0

    for index, error in enumerate(errors, start=1):
        print(f"{index}. {error}")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
