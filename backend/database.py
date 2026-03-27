"""database.py — Supabase (PostgreSQL) — ตาราง gold_*"""
import logging
from datetime import datetime, timezone
from supabase import create_client, Client
from config import SUPABASE_URL, SUPABASE_KEY

logger = logging.getLogger(__name__)

_client: Client = None


def get_client() -> Client:
    global _client
    if _client is None:
        _client = create_client(SUPABASE_URL, SUPABASE_KEY)
        logger.info("✅ Supabase connected")
    return _client


def init_db():
    """ตรวจการเชื่อมต่อ — ตารางสร้างจาก migrations/001_create_tables.sql"""
    try:
        get_client().table("gold_channels").select("id").limit(1).execute()
        logger.info("✅ Supabase tables verified")
    except Exception as e:
        logger.error(f"❌ Supabase error: {e}")
        logger.error("Run migrations/001_create_tables.sql in Supabase SQL Editor first")
        raise


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


# ── Channel CRUD ──────────────────────────────────────────────────────────────

def upsert_channel(name: str, telegram_id: str, description: str = "") -> int:
    res = get_client().table("gold_channels").upsert(
        {"name": name, "telegram_id": telegram_id, "description": description},
        on_conflict="telegram_id"
    ).execute()
    return res.data[0]["id"]


def get_channels():
    res = get_client().table("gold_channels") \
        .select("*").eq("is_active", True).order("name").execute()
    return res.data or []


# ── Signal CRUD ───────────────────────────────────────────────────────────────

def signal_exists(channel_name: str, action: str, entry_price: float, signal_time: str) -> bool:
    """Check duplicate before insert"""
    res = get_client().table("gold_signals") \
        .select("id") \
        .eq("channel_name", channel_name) \
        .eq("action", action) \
        .eq("entry_price", entry_price) \
        .eq("signal_time", signal_time) \
        .limit(1).execute()
    return bool(res.data)


def insert_signal(data: dict) -> int:
    payload = {
        "channel_id":        data.get("channel_id"),
        "channel_name":      data.get("channel_name"),
        "action":            data.get("action"),
        "entry_price":       data.get("entry_price"),
        "tp1":               data.get("tp1"),
        "tp2":               data.get("tp2"),
        "sl":                data.get("sl"),
        "risk_reward_ratio": data.get("risk_reward_ratio"),
        "confidence_score":  data.get("confidence_score"),
        "signal_time":       data.get("signal_time"),
        "order_status":      data.get("order_status", "pending"),
        "raw_message":       data.get("raw_message", "")[:2000],
        "parse_error":       data.get("parse_error"),
    }
    res = get_client().table("gold_signals").insert(payload).execute()
    return res.data[0]["id"]


def update_signal_status(signal_id: int, status: str,
                          result_time: str = None, profit_points: float = None,
                          open_price: float = None, open_time: str = None):
    payload = {"order_status": status}
    if result_time:   payload["result_time"]      = result_time
    if profit_points is not None: payload["profit_points"] = profit_points
    if open_price:    payload["order_open_price"] = open_price
    if open_time:     payload["order_open_time"]  = open_time
    get_client().table("gold_signals").update(payload).eq("id", signal_id).execute()


def get_signals(page: int = 1, limit: int = 50,
                channel: str = None, status: str = None,
                action: str = None, from_date: str = None, to_date: str = None):
    q = get_client().table("gold_signals").select("*", count="exact")
    if channel:   q = q.eq("channel_name", channel)
    if status:    q = q.eq("order_status", status)
    if action:    q = q.eq("action", action)
    if from_date: q = q.gte("signal_time", from_date)
    if to_date:   q = q.lte("signal_time", to_date)

    offset = (page - 1) * limit
    res = q.order("signal_time", desc=True).range(offset, offset + limit - 1).execute()
    return {"total": res.count or 0, "page": page, "limit": limit, "data": res.data or []}


def get_pending_signals():
    res = get_client().table("gold_signals") \
        .select("*") \
        .in_("order_status", ["pending", "open"]) \
        .order("signal_time").execute()
    return res.data or []


def get_signal_markers(from_date: str, to_date: str):
    res = get_client().table("gold_signals") \
        .select("id,action,entry_price,tp1,tp2,sl,signal_time,order_status,profit_points,channel_name") \
        .gte("signal_time", from_date) \
        .lte("signal_time", to_date) \
        .order("signal_time").execute()
    return res.data or []


# ── Price CRUD ────────────────────────────────────────────────────────────────

def insert_prices(rows: list[dict]):
    if not rows:
        return
    # upsert on timestamp unique constraint
    chunk = 500
    for i in range(0, len(rows), chunk):
        try:
            get_client().table("gold_prices") \
                .upsert(rows[i:i + chunk], on_conflict="timestamp").execute()
        except Exception as e:
            logger.warning(f"insert_prices error: {e}")


def get_prices(from_ts: str, to_ts: str):
    res = get_client().table("gold_prices") \
        .select("*") \
        .gte("timestamp", from_ts) \
        .lte("timestamp", to_ts) \
        .order("timestamp").execute()
    return res.data or []


def get_latest_price() -> dict:
    """ดึงแถวล่าสุดจาก gold_prices"""
    res = get_client().table("gold_prices") \
        .select("timestamp,open,high,low,close,volume") \
        .order("timestamp", desc=True).limit(1).execute()
    return res.data[0] if res.data else {}


def get_price_candles(from_ts: str, to_ts: str, interval: str = "1h"):
    """ดึง candles raw แล้ว aggregate ฝั่ง Python"""
    rows = get_prices(from_ts, to_ts)
    if not rows:
        return []

    # truncate timestamp to interval boundary → valid ISO string for JS Date()
    def _bucket_key(ts: str) -> str:
        s = str(ts)[:19]  # "2026-03-27 16:25:23"
        if interval == "1d":  return s[:10]              # "2026-03-27"
        if interval == "1h":  return s[:13] + ":00:00"   # "2026-03-27 16:00:00"
        if interval == "5m":
            m = (int(s[14:16]) // 5) * 5
            return s[:13] + f":{m:02d}:00"              # "2026-03-27 16:25:00"
        return s[:16] + ":00"                            # 1m → "2026-03-27 16:25:00"

    buckets: dict[str, dict] = {}
    for r in rows:
        ts_key = _bucket_key(r["timestamp"])
        if ts_key not in buckets:
            buckets[ts_key] = {"time": ts_key, "open": r["open"],
                                "high": r["high"], "low": r["low"],
                                "close": r["close"], "volume": r.get("volume", 0) or 0}
        else:
            b = buckets[ts_key]
            b["high"]   = max(b["high"],   r["high"]  or b["high"])
            b["low"]    = min(b["low"],    r["low"]   or b["low"])
            b["close"]  = r["close"]
            b["volume"] += r.get("volume", 0) or 0
    return list(buckets.values())


def get_price_range(from_ts: str, to_ts: str) -> dict:
    rows = get_prices(from_ts, to_ts)
    if not rows:
        return {"min_low": None, "max_high": None}
    return {
        "min_low":  min(r["low"]  for r in rows if r["low"]  is not None),
        "max_high": max(r["high"] for r in rows if r["high"] is not None),
    }


# ── Stats ─────────────────────────────────────────────────────────────────────

def get_stats_daily(days: int = 30):
    """ดึงข้อมูล signals ย้อนหลัง N วัน แล้ว aggregate ฝั่ง Python"""
    from datetime import timedelta
    since = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()
    res = get_client().table("gold_signals") \
        .select("signal_time,order_status,profit_points") \
        .gte("signal_time", since) \
        .neq("order_status", "pending") \
        .order("signal_time").execute()

    rows = res.data or []
    daily: dict[str, dict] = {}
    for r in rows:
        date = str(r["signal_time"])[:10]
        if date not in daily:
            daily[date] = {"date": date, "total": 0, "wins": 0,
                           "losses": 0, "total_profit": 0.0}
        d = daily[date]
        d["total"] += 1
        status = r["order_status"]
        profit = r.get("profit_points") or 0
        if status in ("tp1_hit", "tp2_hit"):
            d["wins"] += 1
        elif status == "sl_hit":
            d["losses"] += 1
        d["total_profit"] = round(d["total_profit"] + profit, 2)

    result = sorted(daily.values(), key=lambda x: x["date"], reverse=True)
    for d in result:
        d["win_rate"] = round(d["wins"] / d["total"] * 100, 1) if d["total"] > 0 else 0
    return result


def get_channel_compare():
    res = get_client().table("gold_signals") \
        .select("channel_name,order_status,profit_points") \
        .neq("order_status", "pending").execute()

    rows = res.data or []
    channels: dict[str, dict] = {}
    for r in rows:
        ch = r["channel_name"] or "Unknown"
        if ch not in channels:
            channels[ch] = {"channel_name": ch, "total": 0, "wins": 0,
                            "losses": 0, "total_profit": 0.0}
        c = channels[ch]
        c["total"] += 1
        status = r["order_status"]
        profit = r.get("profit_points") or 0
        if status in ("tp1_hit", "tp2_hit"):
            c["wins"] += 1
        elif status == "sl_hit":
            c["losses"] += 1
        c["total_profit"] = round(c["total_profit"] + profit, 2)

    result = sorted(channels.values(), key=lambda x: x["total_profit"], reverse=True)
    for c in result:
        c["win_rate"] = round(c["wins"] / c["total"] * 100, 1) if c["total"] > 0 else 0
    return result
