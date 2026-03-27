"""telegram_listener.py — Receive messages from Telegram channels via Telethon"""
import asyncio
import base64
import logging
import os
from datetime import datetime, timezone
from telethon import TelegramClient, events
from telethon.errors import FloodWaitError, SessionPasswordNeededError
from telethon.sessions import StringSession
from config import (TELEGRAM_API_ID, TELEGRAM_API_HASH,
                    TELEGRAM_CHANNELS, TELEGRAM_SESSION)
import database as db
from signal_parser import parse_signal, calc_rr

logger = logging.getLogger(__name__)

_client: TelegramClient | None = None
_last_message_ids: dict[str, int] = {}


def _restore_session():
    """Decode TELEGRAM_SESSION_B64 env var and write session file (for cloud deploys)."""
    b64 = os.getenv("TELEGRAM_SESSION_B64", "")
    if not b64:
        return
    session_file = f"{TELEGRAM_SESSION}.session"
    if os.path.exists(session_file):
        return  # already exists locally
    try:
        with open(session_file, "wb") as f:
            f.write(base64.b64decode(b64))
        logger.info("Session restored from TELEGRAM_SESSION_B64")
    except Exception as e:
        logger.error(f"Failed to restore session: {e}")
_running = False


async def _process_message(channel_name: str, channel_tg_id: str,
                            message_text: str, message_time: str):
    """Parse และบันทึก signal จาก message"""
    if not message_text:
        return

    parsed = parse_signal(message_text)

    if not parsed.get("is_signal"):
        reason = parsed.get("reason", "not a signal")
        logger.debug(f"[{channel_name}] ข้าม: {reason}")
        return

    # ดึง/สร้าง channel record
    channel_id = db.upsert_channel(channel_name, channel_tg_id)

    action = parsed.get("action")
    entry  = parsed.get("entry_price")
    tp1    = parsed.get("tp1")
    tp2    = parsed.get("tp2")
    sl     = parsed.get("sl")
    conf   = parsed.get("confidence", 0.0)

    rr = calc_rr(action, entry, tp1, sl) if all([action, entry, tp1, sl]) else None

    # skip duplicate signals
    if db.signal_exists(channel_name, action, entry, message_time):
        logger.debug(f"Duplicate signal skipped [{channel_name}] {action} @ {entry}")
        return

    signal_id = db.insert_signal({
        "channel_id":        channel_id,
        "channel_name":      channel_name,
        "action":            action,
        "entry_price":       entry,
        "tp1":               tp1,
        "tp2":               tp2,
        "sl":                sl,
        "risk_reward_ratio": rr,
        "confidence_score":  conf,
        "signal_time":       message_time,
        "order_status":      "pending",
        "raw_message":       message_text[:2000],
        "parse_error":       None,
    })

    logger.info(
        f"✅ Signal #{signal_id} [{channel_name}] "
        f"{action.upper()} @ {entry} | TP1={tp1} TP2={tp2} SL={sl} | RR={rr}"
    )

    # broadcast ผ่าน WebSocket (ถ้า api.py import ฟังก์ชันนี้)
    try:
        from api import broadcast_new_signal
        await broadcast_new_signal(signal_id)
    except Exception:
        pass


async def _recover_missed_messages(client: TelegramClient):
    """ตอน reconnect — ดึง message ที่หายไประหว่าง offline"""
    logger.info("Recovering missed messages...")
    for channel in TELEGRAM_CHANNELS:
        try:
            last_id = _last_message_ids.get(channel, 0)
            async for msg in client.iter_messages(channel, min_id=last_id, limit=50):
                if msg.text:
                    ts = msg.date.strftime("%Y-%m-%d %H:%M:%S")
                    await _process_message(channel, str(channel), msg.text, ts)
                _last_message_ids[channel] = max(
                    _last_message_ids.get(channel, 0), msg.id
                )
        except Exception as e:
            logger.warning(f"Recover error [{channel}]: {e}")


async def start_listener():
    global _client, _running
    _running = True
    _restore_session()

    retry_delay = 5
    while _running:
        try:
            string_session = os.getenv("TELEGRAM_STRING_SESSION", "")
            session = StringSession(string_session) if string_session else TELEGRAM_SESSION
            _client = TelegramClient(session, TELEGRAM_API_ID, TELEGRAM_API_HASH)
            await _client.start()
            logger.info("✅ Telegram connected")
            retry_delay = 5  # reset backoff

            await _recover_missed_messages(_client)

            # Register event handler
            @_client.on(events.NewMessage(chats=TELEGRAM_CHANNELS))
            async def handler(event):
                try:
                    channel = getattr(event.chat, "username", None) or str(event.chat_id)
                    _last_message_ids[channel] = event.message.id
                    ts = event.message.date.strftime("%Y-%m-%d %H:%M:%S")
                    await _process_message(channel, str(event.chat_id),
                                           event.message.text or "", ts)
                except Exception as e:
                    logger.error(f"Handler error: {e}")

            logger.info(f"Listening to: {TELEGRAM_CHANNELS}")
            await _client.run_until_disconnected()

        except FloodWaitError as e:
            logger.warning(f"FloodWait — รอ {e.seconds}s")
            await asyncio.sleep(e.seconds)
        except (ConnectionError, OSError) as e:
            logger.warning(f"Connection lost: {e} — retry in {retry_delay}s")
            await asyncio.sleep(retry_delay)
            retry_delay = min(retry_delay * 2, 300)  # exponential backoff max 5 นาที
        except Exception as e:
            logger.error(f"Telegram error: {e} — retry in {retry_delay}s")
            await asyncio.sleep(retry_delay)
            retry_delay = min(retry_delay * 2, 300)
        finally:
            if _client and _client.is_connected():
                await _client.disconnect()


async def stop():
    global _running
    _running = False
    if _client and _client.is_connected():
        await _client.disconnect()
