"""signal_parser.py — แปลง Telegram message → structured signal ด้วย Claude API"""
import json
import hashlib
import logging
import re
from anthropic import Anthropic
from config import CLAUDE_API_KEY, CLAUDE_MODEL

logger = logging.getLogger(__name__)
client = Anthropic(api_key=CLAUDE_API_KEY)

# ── Pre-filter: ข้ามข้อความที่ไม่ใช่ signal ────────────────────────────────
_SIGNAL_KEYWORDS = re.compile(
    r'\b(buy|sell|long|short|gold|xau|entry|tp|sl|take profit|stop loss'
    r'|ซื้อ|ขาย|ทอง|เปิด|ปิด)\b',
    re.IGNORECASE
)

# ── Cache: pattern เดิมไม่เรียก Claude ซ้ำ ─────────────────────────────────
_parse_cache: dict[str, dict] = {}
_CACHE_MAX = 500


def _cache_key(text: str) -> str:
    return hashlib.md5(text.strip().lower().encode()).hexdigest()


def is_signal_message(text: str) -> bool:
    """Pre-filter: ตรวจก่อนเรียก Claude — ประหยัด API cost"""
    if len(text.strip()) < 10:
        return False
    return bool(_SIGNAL_KEYWORDS.search(text))


_PROMPT = """You are a gold trading signal parser. Extract trading signal data from the message below.

Return ONLY valid JSON, no explanation. If this is NOT a trading signal, return {"is_signal": false}.

If it IS a signal, return:
{
  "is_signal": true,
  "action": "buy" or "sell",
  "entry_price": <number or null>,
  "tp1": <number or null>,
  "tp2": <number or null>,
  "sl": <number or null>,
  "confidence": <0.0-1.0>
}

Rules:
- entry_price: the price to enter the trade
- tp1: first take profit level
- tp2: second take profit level (optional)
- sl: stop loss level
- confidence: how confident you are (1.0 = very clear signal)
- All prices must be positive numbers
- For BUY: entry < tp1, entry > sl
- For SELL: entry > tp1, entry < sl

Message:
"""


def parse_signal(raw_message: str) -> dict:
    """Parse Telegram message → signal dict. Returns error dict on failure."""

    if not is_signal_message(raw_message):
        return {"is_signal": False, "reason": "pre-filter: no signal keywords"}

    key = _cache_key(raw_message)
    if key in _parse_cache:
        logger.debug("Cache hit — skip Claude API call")
        return _parse_cache[key]

    try:
        response = client.messages.create(
            model=CLAUDE_MODEL,
            max_tokens=256,
            messages=[{"role": "user", "content": _PROMPT + raw_message}]
        )
        text = response.content[0].text.strip()

        # ลอง extract JSON จาก response
        json_match = re.search(r'\{.*\}', text, re.DOTALL)
        if not json_match:
            return {"is_signal": False, "reason": "no JSON in response"}

        result = json.loads(json_match.group())

        # Validate ถ้าเป็น signal
        if result.get("is_signal"):
            error = _validate(result)
            if error:
                return {"is_signal": False, "reason": f"validation: {error}",
                        "raw_parse": result}

        # Cache ผล
        if len(_parse_cache) >= _CACHE_MAX:
            oldest = next(iter(_parse_cache))
            del _parse_cache[oldest]
        _parse_cache[key] = result

        return result

    except json.JSONDecodeError as e:
        logger.warning(f"JSON parse error: {e}")
        return {"is_signal": False, "reason": f"json_error: {e}"}
    except Exception as e:
        logger.error(f"Claude API error: {e}")
        return {"is_signal": False, "reason": f"api_error: {e}"}


def _validate(parsed: dict) -> str | None:
    """Validate parsed signal. คืน error message หรือ None ถ้า OK"""
    action = parsed.get("action", "").lower()
    entry  = parsed.get("entry_price")
    tp1    = parsed.get("tp1")
    sl     = parsed.get("sl")

    if action not in ("buy", "sell"):
        return f"action ไม่ถูกต้อง: {action}"
    if not entry or entry <= 0:
        return f"entry_price ไม่ถูกต้อง: {entry}"
    if not tp1 or tp1 <= 0:
        return f"tp1 ไม่ถูกต้อง: {tp1}"
    if not sl or sl <= 0:
        return f"sl ไม่ถูกต้อง: {sl}"

    if action == "buy":
        if entry >= tp1:
            return f"BUY: entry({entry}) ต้องน้อยกว่า tp1({tp1})"
        if entry <= sl:
            return f"BUY: entry({entry}) ต้องมากกว่า sl({sl})"
    elif action == "sell":
        if entry <= tp1:
            return f"SELL: entry({entry}) ต้องมากกว่า tp1({tp1})"
        if entry >= sl:
            return f"SELL: entry({entry}) ต้องน้อยกว่า sl({sl})"

    return None


def calc_rr(action: str, entry: float, tp1: float, sl: float) -> float | None:
    """คำนวณ Risk/Reward ratio"""
    try:
        reward = abs(tp1 - entry)
        risk   = abs(entry - sl)
        return round(reward / risk, 2) if risk > 0 else None
    except Exception:
        return None
