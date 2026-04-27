"""Telegram long-polling worker.

No webhook → no inbound tunnel needed. We pull updates from
https://api.telegram.org with getUpdates and reply with sendMessage.

Allowlist enforcement: TELEGRAM_ALLOW_USER_IDS in settings.
"""
from __future__ import annotations

import asyncio
import logging

import httpx

import settings
from milo_bridge import respond

log = logging.getLogger("telegram")

API_BASE = "https://api.telegram.org/bot{token}"


async def telegram_worker() -> None:
    if not settings.TELEGRAM_BOT_TOKEN:
        return
    base = API_BASE.format(token=settings.TELEGRAM_BOT_TOKEN)
    offset: int | None = None
    async with httpx.AsyncClient(timeout=httpx.Timeout(60.0, read=65.0)) as client:
        while True:
            try:
                params: dict = {"timeout": 50}
                if offset is not None:
                    params["offset"] = offset
                r = await client.get(f"{base}/getUpdates", params=params)
                r.raise_for_status()
                data = r.json()
                for update in data.get("result", []):
                    offset = max(offset or 0, update["update_id"] + 1)
                    await _handle_update(client, base, update)
            except httpx.HTTPError as exc:
                log.warning("telegram poll error: %s — backing off 5s", exc)
                await asyncio.sleep(5)
            except asyncio.CancelledError:
                raise
            except Exception:
                log.exception("telegram unexpected error — backing off 10s")
                await asyncio.sleep(10)


async def _handle_update(client: httpx.AsyncClient, base: str, update: dict) -> None:
    msg = update.get("message") or update.get("edited_message")
    if not msg:
        return
    user = msg.get("from") or {}
    user_id = user.get("id")
    text = msg.get("text") or ""
    chat_id = (msg.get("chat") or {}).get("id")
    if not (user_id and chat_id and text):
        return
    if settings.TELEGRAM_ALLOW_USER_IDS and user_id not in settings.TELEGRAM_ALLOW_USER_IDS:
        log.info("dropped telegram message from non-allowlisted user %s", user_id)
        return

    log.info("telegram message from %s: len=%d", user_id, len(text))
    reply = await respond(text, "telegram", str(user_id))
    # Telegram caps single message at 4096 chars; chunk if needed.
    for chunk in _chunks(reply, 4000):
        await client.post(f"{base}/sendMessage", json={"chat_id": chat_id, "text": chunk})


def _chunks(s: str, n: int):
    if not s:
        yield ""
        return
    for i in range(0, len(s), n):
        yield s[i:i + n]
