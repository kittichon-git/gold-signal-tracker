"""Run once locally to generate a Telegram StringSession for cloud deployment."""
from telethon.sync import TelegramClient
from telethon.sessions import StringSession
from config import TELEGRAM_API_ID, TELEGRAM_API_HASH

with TelegramClient(StringSession(), TELEGRAM_API_ID, TELEGRAM_API_HASH) as client:
    print("\n✅ Your session string (add to Render as TELEGRAM_STRING_SESSION):\n")
    print(client.session.save())
    print()
