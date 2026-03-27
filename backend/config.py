"""config.py — Load configuration from .env with validation"""
import os
from dotenv import load_dotenv

load_dotenv()

# -- Telegram ------------------------------------------------------------------
TELEGRAM_API_ID    = int(os.getenv("TELEGRAM_API_ID", "0"))
TELEGRAM_API_HASH  = os.getenv("TELEGRAM_API_HASH", "")
TELEGRAM_CHANNELS  = [c.strip() for c in os.getenv("TELEGRAM_CHANNELS", "").split(",") if c.strip()]
TELEGRAM_SESSION   = os.getenv("TELEGRAM_SESSION", "gold_tracker_session")

# -- Claude API ----------------------------------------------------------------
CLAUDE_API_KEY     = os.getenv("CLAUDE_API_KEY", "")
CLAUDE_MODEL       = os.getenv("CLAUDE_MODEL", "claude-haiku-4-5-20251001")

# -- Price Data ----------------------------------------------------------------
TWELVE_DATA_KEY      = os.getenv("TWELVE_DATA_KEY", "")
ALPHA_VANTAGE_KEY    = os.getenv("ALPHA_VANTAGE_KEY", "")
PRICE_FETCH_INTERVAL = int(os.getenv("PRICE_FETCH_INTERVAL", "60"))  # seconds

# -- Supabase ------------------------------------------------------------------
SUPABASE_URL  = os.getenv("SUPABASE_URL", "")
SUPABASE_KEY  = os.getenv("SUPABASE_KEY", "")

# -- App -----------------------------------------------------------------------
BACKEND_PORT    = int(os.getenv("PORT", os.getenv("BACKEND_PORT", "8000")))
API_SECRET_KEY  = os.getenv("API_SECRET_KEY", "change-this-secret-key")
FRONTEND_URL    = os.getenv("FRONTEND_URL", "http://localhost:5173")

# -- Signal Logic --------------------------------------------------------------
SIGNAL_EXPIRY_HOURS = int(os.getenv("SIGNAL_EXPIRY_HOURS", "24"))
ANALYZER_INTERVAL   = int(os.getenv("ANALYZER_INTERVAL", "60"))  # seconds


def validate():
    errors = []
    if not TELEGRAM_API_ID:
        errors.append("TELEGRAM_API_ID is not set")
    if not TELEGRAM_API_HASH:
        errors.append("TELEGRAM_API_HASH is not set")
    if not CLAUDE_API_KEY:
        errors.append("CLAUDE_API_KEY is not set")
    if not TELEGRAM_CHANNELS:
        errors.append("TELEGRAM_CHANNELS is not set")
    if not SUPABASE_KEY:
        errors.append("SUPABASE_KEY is not set")
    if not SUPABASE_URL:
        errors.append("SUPABASE_URL is not set")
    return errors
