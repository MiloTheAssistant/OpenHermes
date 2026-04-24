"""Prompt-injection sanitizer for user-originated content before memory writes.

Every piece of external content (chat inbound, email, scraped web, uploaded
documents) passes through this sanitizer before Milo is allowed to write it
to `workspace/memory/MEMORY.md` or `USER.md`.

This is NOT a silver bullet — a determined attacker can still craft content
that slips through. The point is raising the bar and catching the common
categories so we're not writing "ignore previous instructions" directly into
Milo's durable memory.

Categories detected:
  - Direct instruction overrides ("ignore previous instructions", "disregard",
    "you are now", "from now on you will", "system:", "assistant:")
  - Role-hijack markers (markdown headers like "## SYSTEM", XML tags
    like <system>, <assistant>, <instructions>)
  - Embedded instruction blocks (triple-backtick blocks with role keywords,
    HTML comment instruction blocks)
  - Unicode deception (zero-width chars, bidi overrides, invisible separators)
  - Credential shapes (API-key-ish patterns)

Output: structured verdict + optionally sanitized text. Milo decides whether
to proceed, reprompt John, or discard.

Usage:
    python3 sanitize-memory.py <<'EOF'
    {"content": "Hi, remember my name is John. I live in Chicago."}
    EOF

Exit codes:
    0 — verdict emitted (safe, suspicious, or blocked); stdout has JSON
    1 — invalid input or unrecoverable error
"""
from __future__ import annotations

import json
import re
import sys
import unicodedata
from dataclasses import dataclass, field
from typing import Any


# --- Detection rules -------------------------------------------------------

# Direct instruction-override phrases. Case-insensitive match on any of these
# raises severity to "blocked".
_OVERRIDE_PATTERNS = [
    re.compile(r"\bignore\s+(?:all\s+)?(?:previous|prior|above|earlier)\s+(?:instructions|prompts|directives|rules)\b", re.IGNORECASE),
    re.compile(r"\bdisregard\s+(?:all\s+)?(?:previous|prior|above|earlier)\b", re.IGNORECASE),
    re.compile(r"\byou\s+are\s+(?:now|actually|really)\s+(?:a|an)\s+", re.IGNORECASE),
    re.compile(r"\bfrom\s+now\s+on[,\s]+you\s+(?:will|shall|must)\b", re.IGNORECASE),
    re.compile(r"\bforget\s+(?:everything|all|what)\s+(?:you|I)\s+(?:said|told|were\s+told)\b", re.IGNORECASE),
    re.compile(r"\bnew\s+(?:system|admin|root)\s+(?:prompt|directive|instruction)\b", re.IGNORECASE),
]

# Role-hijack markers. Raising severity to at least "suspicious", "blocked" if
# combined with override pattern.
_ROLE_HIJACK_PATTERNS = [
    re.compile(r"^(?:#{1,6}\s+)?(?:SYSTEM|ASSISTANT|USER|DEVELOPER|TOOL)(?:\s*:|$)", re.IGNORECASE | re.MULTILINE),
    re.compile(r"<(?:system|assistant|user|developer|tool|instructions?)\b[^>]*>", re.IGNORECASE),
    re.compile(r"\[(?:system|assistant|user|developer|instructions?)\]", re.IGNORECASE),
    re.compile(r"^\s*(?:System|Assistant|User|Developer|Tool)\s*(?:Prompt|Message|Role)?\s*:", re.IGNORECASE | re.MULTILINE),
]

# HTML/markdown comment instruction embedding
_COMMENT_INSTRUCTION_PATTERNS = [
    re.compile(r"<!--\s*(?:system|instructions?|admin|override|prompt)", re.IGNORECASE),
    re.compile(r"\[//\]\s*:\s*#?\s*\(\s*(?:system|instructions?|admin)", re.IGNORECASE),
]

# Credential shape detection (single-line, high-entropy-ish)
_CREDENTIAL_PATTERNS = [
    # OpenAI-style keys allow hyphens (e.g. sk-proj-XXX), so allow [_\-] in the tail
    re.compile(r"\b(?:sk|pk)-[A-Za-z0-9_\-]{20,}\b"),
    re.compile(r"\b(?:nvapi|shpat|ghp|glpat|pplx|xai|ctx7|gho)[_\-][A-Za-z0-9_\-]{16,}\b", re.IGNORECASE),
    re.compile(r"\bAKIA[0-9A-Z]{16}\b"),                 # AWS access key
    re.compile(r"\b(?:eyJ[A-Za-z0-9_-]{20,}\.){2,}[A-Za-z0-9_-]{10,}\b"),  # JWT shape
    re.compile(r"(?i)(?:api[_-]?key|token|secret|password)\s*[:=]\s*[\"']?[A-Za-z0-9_\-\.]{16,}"),
]

# Unicode deception: zero-width chars, bidi overrides, control chars
_DECEPTIVE_UNICODE_CATEGORIES = {"Cf", "Mn"}  # format chars + non-spacing marks
_DECEPTIVE_CODEPOINTS = frozenset({
    0x200B, 0x200C, 0x200D, 0x2060,           # zero-width space/joiner/non-joiner/word-joiner
    0x202A, 0x202B, 0x202C, 0x202D, 0x202E,   # LRE, RLE, PDF, LRO, RLO (bidi)
    0x2066, 0x2067, 0x2068, 0x2069,           # LRI, RLI, FSI, PDI
    0xFEFF,                                    # BOM / zero-width no-break space
})


# --- Verdict -------------------------------------------------------------

@dataclass
class Verdict:
    severity: str  # "safe" | "suspicious" | "blocked"
    findings: list[dict[str, Any]] = field(default_factory=list)
    sanitized_text: str = ""
    original_length: int = 0
    sanitized_length: int = 0

    def to_dict(self) -> dict[str, Any]:
        return {
            "verdict": self.severity,
            "findings": self.findings,
            "original_length": self.original_length,
            "sanitized_length": self.sanitized_length,
            "sanitized_text": self.sanitized_text,
            "untrusted_origin_marker": "[[untrusted-origin: sanitized]]",
        }


def _find_all(patterns: list[re.Pattern[str]], text: str, category: str) -> list[dict[str, Any]]:
    results: list[dict[str, Any]] = []
    for p in patterns:
        for m in p.finditer(text):
            results.append({
                "category": category,
                "pattern": p.pattern[:80],
                "match": m.group(0)[:160],
                "start": m.start(),
                "end": m.end(),
            })
    return results


def _find_deceptive_unicode(text: str) -> list[dict[str, Any]]:
    results: list[dict[str, Any]] = []
    for i, ch in enumerate(text):
        cp = ord(ch)
        if cp in _DECEPTIVE_CODEPOINTS or (
            unicodedata.category(ch) in _DECEPTIVE_UNICODE_CATEGORIES and cp > 0x7F
        ):
            results.append({
                "category": "deceptive_unicode",
                "codepoint": f"U+{cp:04X}",
                "unicode_category": unicodedata.category(ch),
                "position": i,
            })
    return results


def sanitize(content: str) -> Verdict:
    """Run content through all detectors and return a verdict."""
    findings: list[dict[str, Any]] = []

    # Collect findings without short-circuiting — surface everything
    overrides = _find_all(_OVERRIDE_PATTERNS, content, "override")
    role_hijacks = _find_all(_ROLE_HIJACK_PATTERNS, content, "role_hijack")
    comment_injections = _find_all(_COMMENT_INSTRUCTION_PATTERNS, content, "comment_injection")
    credentials = _find_all(_CREDENTIAL_PATTERNS, content, "credential")
    deceptive_unicode = _find_deceptive_unicode(content)

    findings = overrides + role_hijacks + comment_injections + credentials + deceptive_unicode

    # Severity mapping:
    #   blocked    — any override pattern OR any credential OR deceptive unicode
    #   suspicious — role_hijack or comment_injection present alone
    #   safe       — no findings
    if overrides or credentials or deceptive_unicode:
        severity = "blocked"
    elif role_hijacks or comment_injections:
        severity = "suspicious"
    else:
        severity = "safe"

    # Sanitization pass — strip deceptive unicode outright, redact credentials,
    # neutralize role-hijack markers by wrapping them in a fence.
    sanitized = content

    # Strip deceptive unicode
    sanitized = "".join(
        ch for ch in sanitized
        if ord(ch) not in _DECEPTIVE_CODEPOINTS
        and not (unicodedata.category(ch) in _DECEPTIVE_UNICODE_CATEGORIES and ord(ch) > 0x7F)
    )

    # Redact credentials
    for p in _CREDENTIAL_PATTERNS:
        sanitized = p.sub("[REDACTED-SECRET]", sanitized)

    # Neutralize role-hijack markers (escape with fence)
    for p in _ROLE_HIJACK_PATTERNS:
        sanitized = p.sub(lambda m: f"\u200B{m.group(0)}\u200B", sanitized)

    return Verdict(
        severity=severity,
        findings=findings,
        sanitized_text=sanitized,
        original_length=len(content),
        sanitized_length=len(sanitized),
    )


def main() -> int:
    # Read JSON payload from stdin or a single file argument
    if len(sys.argv) > 2:
        print("usage: sanitize-memory.py [payload.json]   (or pipe JSON to stdin)", file=sys.stderr)
        return 1
    try:
        raw = open(sys.argv[1], encoding="utf-8").read() if len(sys.argv) == 2 else sys.stdin.read()
        if not raw.strip():
            print("no content provided", file=sys.stderr)
            return 1
        data = json.loads(raw)
    except json.JSONDecodeError as exc:
        print(f"invalid JSON: {exc}", file=sys.stderr)
        return 1

    content = data.get("content") if isinstance(data, dict) else None
    if not isinstance(content, str):
        print("payload must be {\"content\": \"...\"}", file=sys.stderr)
        return 1

    verdict = sanitize(content)
    print(json.dumps(verdict.to_dict(), indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
