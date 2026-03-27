"""main.py — Entry point: เริ่ม backend services ทั้งหมด"""
import asyncio
import logging
import signal
import sys
import uvicorn
from config import BACKEND_PORT, validate
import database as db
from api import app
import price_fetcher
import signal_analyzer
import telegram_listener

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)-8s %(name)-16s %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler("gold_tracker.log", encoding="utf-8"),
    ]
)
logger = logging.getLogger("main")


async def main():
    # ── Validate config ───────────────────────────────────────
    errors = validate()
    if errors:
        for e in errors:
            logger.error(f"Config error: {e}")
        logger.error("แก้ไข .env ก่อนรัน — ดู INSTALL.md")
        sys.exit(1)

    # ── Init DB ───────────────────────────────────────────────
    db.init_db()

    # ── Start background services ─────────────────────────────
    tasks = [
        asyncio.create_task(price_fetcher.price_loop(),       name="price_fetcher"),
        asyncio.create_task(signal_analyzer.analyzer_loop(),  name="signal_analyzer"),
        asyncio.create_task(telegram_listener.start_listener(), name="telegram"),
    ]

    # ── Start FastAPI ─────────────────────────────────────────
    config = uvicorn.Config(
        app=app,
        host="0.0.0.0",
        port=BACKEND_PORT,
        log_level="warning",
    )
    server = uvicorn.Server(config)

    logger.info(f"🚀 Gold Signal Tracker started — http://localhost:{BACKEND_PORT}")
    logger.info(f"   API Docs: http://localhost:{BACKEND_PORT}/docs")

    # Graceful shutdown
    def shutdown(*_):
        logger.info("Shutting down...")
        price_fetcher.stop()
        signal_analyzer.stop()
        asyncio.create_task(telegram_listener.stop())
        for t in tasks:
            t.cancel()

    signal.signal(signal.SIGINT,  shutdown)
    signal.signal(signal.SIGTERM, shutdown)

    await asyncio.gather(server.serve(), *tasks, return_exceptions=True)


if __name__ == "__main__":
    asyncio.run(main())
