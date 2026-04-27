"""Settings loader — reads ~/.openhermes/milo-daemon.env (mode 0600)."""
from __future__ import annotations

import os
from pathlib import Path
from dotenv import load_dotenv

ENV_PATH = Path.home() / ".openhermes" / "milo-daemon.env"
if ENV_PATH.exists():
    load_dotenv(ENV_PATH)


def _split_csv(name: str) -> list[str]:
    raw = os.getenv(name, "")
    return [x.strip() for x in raw.split(",") if x.strip()]


HOST = os.getenv("MILO_DAEMON_HOST", "127.0.0.1")
PORT = int(os.getenv("MILO_DAEMON_PORT", "18790"))

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_ALLOW_USER_IDS = {int(x) for x in _split_csv("TELEGRAM_ALLOW_USER_IDS")}

DISCORD_BOT_TOKEN = os.getenv("DISCORD_BOT_TOKEN", "")
DISCORD_ALLOW_USER_IDS = set(_split_csv("DISCORD_ALLOW_USER_IDS"))
DISCORD_ALLOW_GUILD_IDS = set(_split_csv("DISCORD_ALLOW_GUILD_IDS"))

OPENCLAW_GATEWAY_URL = os.getenv("OPENCLAW_GATEWAY_URL", "http://127.0.0.1:18789")

# Path to bridge scripts (classifier, sanitizer, delegate-to-elon)
OPENHERMES_ROOT = Path(__file__).resolve().parent.parent
BRIDGE_DIR = OPENHERMES_ROOT / "bridge" / "scripts"
