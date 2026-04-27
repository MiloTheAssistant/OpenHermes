"""milo_bridge — invoke Milo (Nous Hermes Agent) for a single user turn.

Phase 13 v1: shells out to the Hermes CLI in non-interactive single-shot mode
using asyncio.create_subprocess_exec (no shell, list-arg form — safe from
command injection). Future: switch to the Hermes SDK / direct gateway call
once we settle on a session-continuity model per user.

The bridge is stateless at this layer — Hermes itself maintains session state
in ~/.hermes/sessions/. We pass --session-key derived from {source}:{user_id}
so each channel-user pair gets its own continuous thread.
"""
from __future__ import annotations

import asyncio
import json
import logging
import re
from pathlib import Path
from typing import Literal

from settings import BRIDGE_DIR

log = logging.getLogger("milo_bridge")

Source = Literal["telegram", "discord", "mission-control", "api", "terminal"]


async def _run_argv(argv: list[str], stdin_text: str | None = None, timeout: float = 600.0) -> tuple[int, str, str]:
    """Spawn argv[0] with argv[1:] (no shell). Returns (rc, stdout, stderr)."""
    proc = await asyncio.create_subprocess_exec(
        *argv,
        stdin=asyncio.subprocess.PIPE if stdin_text is not None else None,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    try:
        out_b, err_b = await asyncio.wait_for(
            proc.communicate(stdin_text.encode() if stdin_text is not None else None),
            timeout=timeout,
        )
    except asyncio.TimeoutError:
        proc.kill()
        await proc.wait()
        return 124, "", f"timeout after {timeout}s"
    return proc.returncode or 0, out_b.decode("utf-8", "replace"), err_b.decode("utf-8", "replace")


async def sanitize(text: str) -> dict:
    """Run the prompt-injection sanitizer. Returns the parsed envelope."""
    script = BRIDGE_DIR / "sanitize-memory.py"
    if not script.exists():
        log.warning("sanitizer not found at %s; passing through", script)
        return {"severity": "safe", "sanitized_text": text, "findings": []}
    rc, out, err = await _run_argv(["python3", str(script), "--stdin"], stdin_text=text, timeout=15)
    if rc != 0:
        log.warning("sanitizer exited %d: %s", rc, err)
        return {"severity": "suspicious", "sanitized_text": text, "findings": [f"sanitizer-error: {err.strip()}"]}
    try:
        return json.loads(out)
    except json.JSONDecodeError:
        return {"severity": "safe", "sanitized_text": text, "findings": []}


async def respond(text: str, source: Source, user_id: str) -> str:
    """Send text to Milo, return Milo's reply (one subprocess per turn).

    Uses verified Hermes CLI flags from `hermes chat --help`:
      -Q              quiet/programmatic mode (no banner/spinner/tool previews)
      -q QUERY        single non-interactive query
      --source TAG    session source tag (filtering)
      --continue NAME resume session by name (best-effort; falls back if absent)

    Phase 13 v1: each turn is a fresh single-query subprocess. Per-user session
    continuity via `--continue {source}-{user_id}` will be wired in Phase 14
    once we verify Hermes session-name semantics empirically.
    """
    findings = await sanitize(text)
    if findings.get("severity") == "blocked":
        return (
            "Milo blocked this message — looked like a prompt-injection "
            "attempt. Findings: " + ", ".join(findings.get("findings", []))
        )
    sanitized = findings.get("sanitized_text", text)

    session_tag = f"{source}-{user_id}"
    # Provider must be explicit — Hermes `provider: auto` resolves to OpenRouter
    # which does not stock `minimax-m2.7:cloud`. Force ollama-cloud.
    argv = [
        "uv", "run", "--project", str(Path.home() / "repos" / "hermes-agent"),
        "hermes", "chat",
        "-Q",
        "--provider", "ollama-cloud",
        "-m", "minimax-m2.7:cloud",
        "--source", source,
        "-q", sanitized,
    ]
    log.info("dispatching to Milo (session_tag=%s, len=%d)", session_tag, len(sanitized))
    rc, out, err = await _run_argv(argv, timeout=600)
    if rc != 0:
        log.error("hermes exit %d, stderr=%s", rc, err[:500])
        return f"Milo errored (rc={rc}). Check ~/.hermes/logs/. Stderr: {err.strip()[:300]}"

    cleaned = _strip_ansi(out).strip()
    return cleaned or "(Milo returned an empty response)"


_ANSI_RE = re.compile(r"\x1b\[[0-9;]*[A-Za-z]")


def _strip_ansi(s: str) -> str:
    return _ANSI_RE.sub("", s)
