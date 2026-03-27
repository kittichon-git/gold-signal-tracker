"""signal_analyzer.py — ตรวจสอบ TP/SL hit และอัปเดตสถานะ signal"""
import asyncio
import logging
from datetime import datetime, timedelta, timezone
from config import ANALYZER_INTERVAL, SIGNAL_EXPIRY_HOURS
import database as db

logger = logging.getLogger(__name__)
_running = False


def _now_str() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")


def analyze_signal(signal: dict) -> tuple[str, float | None]:
    """
    วิเคราะห์ signal 1 ตัว โดยดูจากข้อมูลราคาใน DB
    คืน (new_status, profit_points)
    """
    signal_time = signal["signal_time"]
    action      = signal["action"]
    entry       = signal["entry_price"]
    tp1         = signal["tp1"]
    tp2         = signal["tp2"]
    sl          = signal["sl"]
    now         = _now_str()

    # ── ตรวจว่าราคาเคยแตะ entry ไหม (เปิด order ได้หรือเปล่า) ────────────
    prices_since = db.get_prices(signal_time, now)
    if not prices_since:
        return signal["order_status"], None  # ยังไม่มีข้อมูลราคา

    # หาว่าเคยแตะ entry ไหม
    entry_hit_idx = None
    for i, p in enumerate(prices_since):
        low  = p["low"]
        high = p["high"]
        if action == "buy"  and low  <= entry <= high:
            entry_hit_idx = i
            break
        if action == "sell" and low  <= entry <= high:
            entry_hit_idx = i
            break

    # ── Missed: ไม่แตะ entry ภายใน SIGNAL_EXPIRY_HOURS ─────────────────────
    expiry = (datetime.fromisoformat(signal_time)
              + timedelta(hours=SIGNAL_EXPIRY_HOURS)).strftime("%Y-%m-%d %H:%M:%S")
    if entry_hit_idx is None:
        if now >= expiry:
            return "missed", None
        return "pending", None

    # ── Order เปิดแล้ว — ตรวจ TP/SL ────────────────────────────────────────
    prices_after_entry = prices_since[entry_hit_idx:]

    for p in prices_after_entry:
        low  = p["low"]
        high = p["high"]

        if action == "buy":
            if tp2 and high >= tp2:
                profit = round(tp2 - entry, 2)
                return "tp2_hit", profit
            if tp1 and high >= tp1:
                profit = round(tp1 - entry, 2)
                return "tp1_hit", profit
            if sl and low <= sl:
                profit = round(sl - entry, 2)
                return "sl_hit", profit

        elif action == "sell":
            if tp2 and low <= tp2:
                profit = round(entry - tp2, 2)
                return "tp2_hit", profit
            if tp1 and low <= tp1:
                profit = round(entry - tp1, 2)
                return "tp1_hit", profit
            if sl and high >= sl:
                profit = round(entry - sl, 2)
                return "sl_hit", profit

    return "open", None


async def analyzer_loop():
    """รัน background loop ตรวจ TP/SL ทุก ANALYZER_INTERVAL วินาที"""
    global _running
    _running = True
    logger.info(f"Signal analyzer started (interval={ANALYZER_INTERVAL}s)")

    while _running:
        try:
            pending = db.get_pending_signals()
            if pending:
                logger.debug(f"Analyzing {len(pending)} pending/open signals...")
            for signal in pending:
                new_status, profit = analyze_signal(signal)
                if new_status != signal["order_status"]:
                    db.update_signal_status(
                        signal_id     = signal["id"],
                        status        = new_status,
                        result_time   = _now_str() if new_status not in ("pending","open") else None,
                        profit_points = profit,
                        open_price    = signal["entry_price"] if new_status == "open" else None,
                        open_time     = _now_str() if new_status == "open" else None,
                    )
                    logger.info(
                        f"Signal #{signal['id']} [{signal['channel_name']}]"
                        f" {signal['action'].upper()} {signal['entry_price']}"
                        f" → {new_status}"
                        + (f" ({profit:+.2f} pts)" if profit is not None else "")
                    )
        except Exception as e:
            logger.error(f"Analyzer error: {e}")

        await asyncio.sleep(ANALYZER_INTERVAL)


def stop():
    global _running
    _running = False
