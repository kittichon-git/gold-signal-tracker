"""price_fetcher.py — ดึงราคา XAUUSD จากหลาย source (fallback chain)"""
import asyncio
import logging
import aiohttp
from datetime import datetime, timezone
from config import TWELVE_DATA_KEY, ALPHA_VANTAGE_KEY, PRICE_FETCH_INTERVAL
import database as db

logger = logging.getLogger(__name__)

SYMBOL_YFINANCE     = "GC=F"       # Gold Futures (yfinance fallback)
SYMBOL_TWELVEDATA   = "XAU/USD"    # Twelve Data
SYMBOL_ALPHAVANTAGE = "XAUUSD"     # Alpha Vantage (Forex)

_running = False


async def fetch_twelvedata(session: aiohttp.ClientSession) -> dict | None:
    if not TWELVE_DATA_KEY:
        return None
    try:
        url = (f"https://api.twelvedata.com/price"
               f"?symbol={SYMBOL_TWELVEDATA}&apikey={TWELVE_DATA_KEY}")
        async with session.get(url, timeout=aiohttp.ClientTimeout(total=10)) as r:
            data = await r.json()
            if "price" in data:
                price = float(data["price"])
                now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
                return {"timestamp": now, "open": price, "high": price,
                        "low": price, "close": price, "volume": 0, "source": "twelvedata"}
    except Exception as e:
        logger.debug(f"Twelve Data error: {e}")
    return None


async def fetch_alphavantage(session: aiohttp.ClientSession) -> dict | None:
    if not ALPHA_VANTAGE_KEY:
        return None
    try:
        url = (f"https://www.alphavantage.co/query"
               f"?function=CURRENCY_EXCHANGE_RATE"
               f"&from_currency=XAU&to_currency=USD"
               f"&apikey={ALPHA_VANTAGE_KEY}")
        async with session.get(url, timeout=aiohttp.ClientTimeout(total=10)) as r:
            data = await r.json()
            rate = data.get("Realtime Currency Exchange Rate", {}).get("5. Exchange Rate")
            if rate:
                price = float(rate)
                now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
                return {"timestamp": now, "open": price, "high": price,
                        "low": price, "close": price, "volume": 0, "source": "alphavantage"}
    except Exception as e:
        logger.debug(f"Alpha Vantage error: {e}")
    return None


async def fetch_yfinance() -> dict | None:
    """Fallback — try multiple symbols"""
    import yfinance as yf
    for symbol in ("GC=F", "XAUUSD=X"):
        try:
            hist = yf.Ticker(symbol).history(period="1d", interval="1m").tail(1)
            if not hist.empty:
                row = hist.iloc[-1]
                ts  = hist.index[-1].strftime("%Y-%m-%d %H:%M:%S")
                return {"timestamp": ts, "open": float(row["Open"]),
                        "high": float(row["High"]), "low": float(row["Low"]),
                        "close": float(row["Close"]), "volume": float(row["Volume"]),
                        "source": f"yfinance_{symbol}"}
        except Exception as e:
            logger.debug(f"yfinance {symbol} error: {e}")
    return None


async def fetch_candles_yfinance(period: str = "7d", interval: str = "1h") -> list[dict]:
    """Load historical candles on startup — try multiple symbols"""
    import yfinance as yf
    for symbol in ("GC=F", "XAUUSD=X"):
        try:
            hist = yf.Ticker(symbol).history(period=period, interval=interval)
            if hist.empty:
                continue
            rows = []
            for ts, row in hist.iterrows():
                rows.append({
                    "timestamp": ts.strftime("%Y-%m-%d %H:%M:%S"),
                    "open":   float(row["Open"]),
                    "high":   float(row["High"]),
                    "low":    float(row["Low"]),
                    "close":  float(row["Close"]),
                    "volume": float(row["Volume"]),
                    "source": f"yfinance_{symbol}"
                })
            if rows:
                return rows
        except Exception as e:
            logger.debug(f"yfinance {symbol} candles error: {e}")
    return []


async def price_loop():
    """รัน background loop ดึงราคาทุก PRICE_FETCH_INTERVAL วินาที"""
    global _running
    _running = True
    logger.info(f"Price fetcher started (interval={PRICE_FETCH_INTERVAL}s)")

    # โหลด historical data ตอนเริ่ม
    logger.info("Loading historical price data (7d / 1h)...")
    candles = await fetch_candles_yfinance("7d", "1h")
    if candles:
        db.insert_prices(candles)
        logger.info(f"  → {len(candles)} historical candles loaded")

    conn = aiohttp.TCPConnector(ssl=True)
    async with aiohttp.ClientSession(connector=conn) as session:
        while _running:
            price = None

            # Fallback chain: Twelve Data → Alpha Vantage → yfinance
            price = await fetch_twelvedata(session)
            if not price:
                price = await fetch_alphavantage(session)
            if not price:
                price = await fetch_yfinance()

            if price:
                db.insert_prices([price])
                logger.debug(f"Price: {price['close']} from {price['source']}")
            else:
                logger.warning("All price sources failed — will retry next interval")

            await asyncio.sleep(PRICE_FETCH_INTERVAL)


def stop():
    global _running
    _running = False
