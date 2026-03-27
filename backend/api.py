"""api.py — FastAPI routes พร้อม Auth, CORS, WebSocket, Rate limiting"""
import logging
from datetime import datetime
from fastapi import FastAPI, Depends, HTTPException, WebSocket, WebSocketDisconnect, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security.api_key import APIKeyHeader
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from starlette.requests import Request
from config import API_SECRET_KEY, FRONTEND_URL
import database as db

logger = logging.getLogger(__name__)

# ── App Setup ─────────────────────────────────────────────────────────────────
limiter = Limiter(key_func=get_remote_address)
app = FastAPI(title="Gold Signal Tracker API", version="1.0.0")
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[FRONTEND_URL, "http://localhost:5173",
                   "https://localhost:5173"],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE"],
    allow_headers=["*"],
)

# ── Auth ──────────────────────────────────────────────────────────────────────
api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)

async def require_api_key(key: str = Depends(api_key_header)):
    if key != API_SECRET_KEY:
        raise HTTPException(status_code=401, detail="Invalid API Key")
    return key

# ── WebSocket Manager ─────────────────────────────────────────────────────────
class ConnectionManager:
    def __init__(self):
        self.active: list[WebSocket] = []

    async def connect(self, ws: WebSocket):
        await ws.accept()
        self.active.append(ws)

    def disconnect(self, ws: WebSocket):
        if ws in self.active:
            self.active.remove(ws)

    async def broadcast(self, data: dict):
        dead = []
        for ws in self.active:
            try:
                await ws.send_json(data)
            except Exception:
                dead.append(ws)
        for ws in dead:
            self.disconnect(ws)

ws_manager = ConnectionManager()


async def broadcast_new_signal(signal_id: int):
    """เรียกจาก telegram_listener เมื่อมี signal ใหม่"""
    await ws_manager.broadcast({"type": "new_signal", "signal_id": signal_id})


# ── Health Check ──────────────────────────────────────────────────────────────
@app.get("/health")
async def health():
    return {"status": "ok", "timestamp": datetime.utcnow().isoformat()}


# ── WebSocket ─────────────────────────────────────────────────────────────────
@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await ws_manager.connect(websocket)
    try:
        while True:
            await websocket.receive_text()  # keep-alive
    except WebSocketDisconnect:
        ws_manager.disconnect(websocket)


# ── Signals ───────────────────────────────────────────────────────────────────
@app.get("/api/signals")
@limiter.limit("60/minute")
async def get_signals(
    request: Request,
    page:     int   = Query(1, ge=1),
    limit:    int   = Query(50, ge=1, le=200),
    channel:  str   = Query(None),
    status:   str   = Query(None),
    action:   str   = Query(None),
    from_date: str  = Query(None),
    to_date:   str  = Query(None),
    _: str = Depends(require_api_key),
):
    return db.get_signals(page, limit, channel, status, action, from_date, to_date)


@app.get("/api/signals/markers")
@limiter.limit("60/minute")
async def get_markers(
    request: Request,
    from_date: str = Query(...),
    to_date:   str = Query(...),
    _: str = Depends(require_api_key),
):
    return db.get_signal_markers(from_date, to_date)


# ── Prices ────────────────────────────────────────────────────────────────────
@app.get("/api/prices")
@limiter.limit("60/minute")
async def get_prices(
    request:  Request,
    from_date: str = Query(...),
    to_date:   str = Query(...),
    interval:  str = Query("1h"),
    _: str = Depends(require_api_key),
):
    return db.get_price_candles(from_date, to_date, interval)


@app.get("/api/price/latest")
@limiter.limit("60/minute")
async def get_latest_price(request: Request, _: str = Depends(require_api_key)):
    return db.get_latest_price()


# ── Stats ─────────────────────────────────────────────────────────────────────
@app.get("/api/stats/daily")
@limiter.limit("30/minute")
async def stats_daily(
    request: Request,
    days: int = Query(30, ge=1, le=365),
    _: str = Depends(require_api_key),
):
    return db.get_stats_daily(days)


@app.get("/api/stats/weekly")
@limiter.limit("30/minute")
async def stats_weekly(request: Request, _: str = Depends(require_api_key)):
    return db.get_stats_daily(90)


@app.get("/api/stats/yearly")
@limiter.limit("30/minute")
async def stats_yearly(request: Request, _: str = Depends(require_api_key)):
    return db.get_stats_daily(365)


# ── Channels ──────────────────────────────────────────────────────────────────
@app.get("/api/channels")
@limiter.limit("30/minute")
async def get_channels(request: Request, _: str = Depends(require_api_key)):
    return db.get_channels()


@app.get("/api/channels/compare")
@limiter.limit("30/minute")
async def channel_compare(request: Request, _: str = Depends(require_api_key)):
    return db.get_channel_compare()
