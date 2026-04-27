"""hermes-daemon — Milo's HTTP front door.

Loopback bind only (127.0.0.1:18790). Exposes /health, /chat, /notify and
runs Telegram + Discord workers in the background via FastAPI lifespan.
"""
from __future__ import annotations

import asyncio
import logging
import time
from contextlib import asynccontextmanager
from typing import Literal

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

import settings
from milo_bridge import respond

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
)
log = logging.getLogger("hermes-daemon")


class ChatRequest(BaseModel):
    user_id: str
    source: Literal["telegram", "discord", "mission-control", "api", "terminal"] = "api"
    text: str = Field(min_length=1, max_length=8000)


class ChatResponse(BaseModel):
    reply: str
    duration_ms: int


class NotifyRequest(BaseModel):
    kind: str
    payload: dict


@asynccontextmanager
async def lifespan(_app: FastAPI):
    workers: list[asyncio.Task] = []
    if settings.TELEGRAM_BOT_TOKEN:
        from telegram_poller import telegram_worker
        workers.append(asyncio.create_task(telegram_worker(), name="telegram"))
        log.info("telegram worker started")
    else:
        log.info("telegram disabled (no token)")

    if settings.DISCORD_BOT_TOKEN:
        from discord_bot import discord_worker
        workers.append(asyncio.create_task(discord_worker(), name="discord"))
        log.info("discord worker started")
    else:
        log.info("discord disabled (no token)")

    try:
        yield
    finally:
        for w in workers:
            w.cancel()
        for w in workers:
            try:
                await w
            except asyncio.CancelledError:
                pass


app = FastAPI(title="Milo daemon", version="13.0.0", lifespan=lifespan)


@app.get("/health")
async def health() -> dict:
    return {
        "ok": True,
        "service": "hermes-daemon",
        "version": "13.0.0",
        "channels": {
            "telegram": bool(settings.TELEGRAM_BOT_TOKEN),
            "discord": bool(settings.DISCORD_BOT_TOKEN),
        },
        "ts": int(time.time()),
    }


@app.post("/chat", response_model=ChatResponse)
async def chat(req: ChatRequest) -> ChatResponse:
    started = time.monotonic()
    try:
        reply = await respond(req.text, req.source, req.user_id)
    except Exception as exc:  # surface to caller, log full trace
        log.exception("chat error")
        raise HTTPException(status_code=500, detail=f"milo error: {exc}") from exc
    duration_ms = int((time.monotonic() - started) * 1000)
    return ChatResponse(reply=reply, duration_ms=duration_ms)


@app.post("/notify")
async def notify(req: NotifyRequest) -> dict:
    """Mission Control → Milo signal sink (approval resolutions, etc.).

    For Phase 13 v1 we record-and-acknowledge. A follow-on will route the
    signal into Milo's session as a system message so he can decide whether
    to surface it to John in the active channel.
    """
    log.info("notify kind=%s payload_keys=%s", req.kind, list(req.payload.keys()))
    return {"received": True, "kind": req.kind}
