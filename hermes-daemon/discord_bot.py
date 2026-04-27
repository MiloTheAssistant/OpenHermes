"""Discord websocket worker.

Uses discord.py's gateway connection — no webhook tunnel needed. The bot
connects outbound, receives MESSAGE_CREATE events over the socket, and replies
in the same channel.

Allowlists: DISCORD_ALLOW_USER_IDS, DISCORD_ALLOW_GUILD_IDS in settings.
"""
from __future__ import annotations

import logging

import discord

import settings
from milo_bridge import respond

log = logging.getLogger("discord")


def _allowed(message: discord.Message) -> bool:
    if settings.DISCORD_ALLOW_USER_IDS and str(message.author.id) not in settings.DISCORD_ALLOW_USER_IDS:
        return False
    if message.guild and settings.DISCORD_ALLOW_GUILD_IDS:
        if str(message.guild.id) not in settings.DISCORD_ALLOW_GUILD_IDS:
            return False
    return True


async def discord_worker() -> None:
    if not settings.DISCORD_BOT_TOKEN:
        return

    intents = discord.Intents.default()
    intents.message_content = True
    client = discord.Client(intents=intents)

    @client.event
    async def on_ready() -> None:  # type: ignore[unused-variable]
        log.info("discord ready as %s", client.user)

    @client.event
    async def on_message(message: discord.Message) -> None:  # type: ignore[unused-variable]
        if message.author == client.user or message.author.bot:
            return
        if not _allowed(message):
            return
        # In guilds, require @-mention; in DMs, always respond.
        if message.guild and client.user not in message.mentions:
            return

        text = message.clean_content.strip()
        if not text:
            return
        log.info("discord message from %s in %s: len=%d", message.author.id, message.guild.id if message.guild else "DM", len(text))

        async with message.channel.typing():
            reply = await respond(text, "discord", str(message.author.id))

        for chunk in _chunks(reply, 1900):  # Discord limit is 2000; leave headroom
            await message.channel.send(chunk)

    try:
        await client.start(settings.DISCORD_BOT_TOKEN)
    finally:
        if not client.is_closed():
            await client.close()


def _chunks(s: str, n: int):
    if not s:
        yield ""
        return
    for i in range(0, len(s), n):
        yield s[i:i + n]
