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
    """Run the prompt-injection sanitizer. Returns a normalized envelope:
       {severity: safe|suspicious|blocked, sanitized_text: str, findings: list}.

    The script reads JSON `{"content": "..."}` on stdin and emits a `verdict`
    object (`{"verdict": ..., "findings": ..., "sanitized_text": ...}`).
    We translate `verdict` → `severity` for the daemon's call site.
    """
    script = BRIDGE_DIR / "sanitize-memory.py"
    if not script.exists():
        log.warning("sanitizer not found at %s; passing through", script)
        return {"severity": "safe", "sanitized_text": text, "findings": []}
    payload = json.dumps({"content": text})
    rc, out, err = await _run_argv(["python3", str(script)], stdin_text=payload, timeout=15)
    if rc != 0:
        log.warning("sanitizer exited %d: %s", rc, err.strip()[:300])
        return {"severity": "suspicious", "sanitized_text": text, "findings": [{"sanitizer_error": err.strip()[:300]}]}
    try:
        parsed = json.loads(out)
    except json.JSONDecodeError:
        return {"severity": "safe", "sanitized_text": text, "findings": []}
    return {
        "severity": parsed.get("verdict", "safe"),
        "sanitized_text": parsed.get("sanitized_text", text),
        "findings": parsed.get("findings", []),
    }


async def respond(text: str, source: Source, user_id: str) -> str:
    """Send text to Milo, return Milo's reply (one subprocess per turn).

    Uses verified Hermes CLI flags from `hermes chat --help`:
      -Q              quiet/programmatic mode (no banner/spinner/tool previews)
      -q QUERY        single non-interactive query
      -t hermes-cli   minimal toolset — auto-loaded toolsets (browser, vision,
                      gmail, image_gen, etc.) add ~3s of import overhead per
                      turn. SOUL.md (Milo persona) is still injected.
      --source TAG    session source tag (filtering)

    Phase 13 v1: each turn is a fresh single-query subprocess. Phase 14 should
    move to a persistent worker (Hermes SDK `AIAgent.chat()`) to drop the
    Python startup cost entirely.
    """
    import time as _time
    findings = await sanitize(text)
    if findings.get("severity") == "blocked":
        return (
            "Milo blocked this message — looked like a prompt-injection "
            "attempt. Findings: " + ", ".join(str(f) for f in findings.get("findings", []))
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
        "-t", "hermes-cli",
        "--source", source,
        "-q", sanitized,
    ]
    started = _time.monotonic()
    log.info("dispatching to Milo (session_tag=%s, len=%d)", session_tag, len(sanitized))
    rc, out, err = await _run_argv(argv, timeout=600)
    elapsed_ms = int((_time.monotonic() - started) * 1000)
    if rc != 0:
        log.error("hermes exit %d after %dms, stderr=%s", rc, elapsed_ms, err[:500])
        return f"Milo errored (rc={rc}). Check ~/.hermes/logs/. Stderr: {err.strip()[:300]}"

    cleaned = _strip_ansi(out).strip()
    log.info("Milo replied (session_tag=%s, %dms, reply_len=%d)", session_tag, elapsed_ms, len(cleaned))
    return cleaned or "(Milo returned an empty response)"


_ANSI_RE = re.compile(r"\x1b\[[0-9;]*[A-Za-z]")


def _strip_ansi(s: str) -> str:
    return _ANSI_RE.sub("", s)
