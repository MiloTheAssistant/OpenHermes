# Codex Brief #3 — Handoff envelope JSON Schema + validator

**Target files:**
- `$OPENHERMES_ROOT/bridge/schemas/handoff.schema.json`
- `$OPENHERMES_ROOT/bridge/scripts/validate_handoff.py`

**Priority:** Blocks Phase 8 (Bridge).

---

## Prompt (paste into Codex)

Produce a strict JSON Schema (Draft 2020-12) for the OpenHermes handoff envelope, plus a Python validator.

### Required top-level fields

| Field | Type | Constraints |
|---|---|---|
| `task_id` | string | ULID format (26 chars, Crockford base32) |
| `origin_agent` | string | enum: `[milo, elon, zuck, sagan, neo, sentinel, cortana, cornelius, kat]` |
| `target_agent` | string | same enum as `origin_agent` |
| `request_summary` | string | max 2000 chars |
| `governance_class` | string | enum: `[info, action, publish, irreversible]` |
| `routing_profile` | string | non-empty |
| `risk_level` | string | enum: `[low, medium, high, critical]` |
| `requires_halt` | boolean | — |
| `budget` | object | see below |
| `artifacts` | array | items: objects (any shape) |
| `status` | string | enum: `[pending, in_progress, awaiting_approval, complete, halted, failed]` |
| `next_action` | string | non-empty |

### Budget object (nested, required)

| Field | Type | Constraints |
|---|---|---|
| `max_tokens` | integer | minimum 1 |
| `max_seconds` | integer | minimum 1 |
| `max_tool_calls` | integer | minimum 1 |

### Optional audit object

| Field | Type | Constraints |
|---|---|---|
| `created_at` | string | ISO 8601 datetime |
| `created_by` | string | — |
| `trace_id` | string | — |

### Schema-level requirements

- `additionalProperties: false` on the root object AND on `budget`
- All `required` arrays populated per the tables above
- Descriptive `description` on every field and meaningful `errorMessage` (or `$comment`) where strict constraints apply
- Use `$id` = `https://openhermes.milotheassistant.dev/schemas/handoff.schema.json` (placeholder URL — does not need to resolve)
- Use `title: "OpenHermes Handoff Envelope"`

### Companion Python validator (`validate_handoff.py`)

Uses the `jsonschema` library. Single entry point:

```python
def validate_handoff(envelope: dict, schema_path: str = None) -> tuple[bool, list[str]]:
    """Validate an envelope dict against the schema.
    Returns (is_valid, errors_list). errors_list is empty on success.
    """
```

Also provide a `__main__` block that:
1. Reads an envelope JSON from stdin (or a file path arg)
2. Validates
3. Prints either `VALID` or a numbered list of errors
4. Exits 0 on valid, 1 on invalid

---

## Acceptance criteria

- Schema validates against a sample valid envelope (provide one in docstring)
- Schema rejects missing required fields
- Schema rejects additional top-level properties
- Schema rejects budget values < 1
- Schema rejects unknown agent IDs
- Validator script handles both stdin and file args
