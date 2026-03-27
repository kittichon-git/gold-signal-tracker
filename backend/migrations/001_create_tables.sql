-- ============================================================
-- Gold Signal Tracker — Supabase Migration
-- วิธีรัน: Supabase Dashboard → SQL Editor → วางแล้วกด Run
-- ============================================================

-- ── gold_channels ─────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS gold_channels (
    id           BIGSERIAL PRIMARY KEY,
    name         TEXT        NOT NULL,
    telegram_id  TEXT        UNIQUE,
    description  TEXT,
    is_active    BOOLEAN     DEFAULT TRUE,
    created_at   TIMESTAMPTZ DEFAULT NOW()
);

-- ── gold_signals ──────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS gold_signals (
    id                 BIGSERIAL PRIMARY KEY,
    channel_id         BIGINT      REFERENCES gold_channels(id),
    channel_name       TEXT,
    action             TEXT        CHECK(action IN ('buy','sell')),
    entry_price        NUMERIC,
    tp1                NUMERIC,
    tp2                NUMERIC,
    sl                 NUMERIC,
    risk_reward_ratio  NUMERIC,
    confidence_score   NUMERIC,
    signal_time        TIMESTAMPTZ,
    order_open_price   NUMERIC,
    order_open_time    TIMESTAMPTZ,
    order_status       TEXT        DEFAULT 'pending'
                       CHECK(order_status IN
                       ('pending','open','tp1_hit','tp2_hit','sl_hit','missed','cancelled')),
    result_time        TIMESTAMPTZ,
    profit_points      NUMERIC,
    raw_message        TEXT,
    parse_error        TEXT,
    created_at         TIMESTAMPTZ DEFAULT NOW(),
    updated_at         TIMESTAMPTZ DEFAULT NOW()
);

-- ── gold_prices ───────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS gold_prices (
    id        BIGSERIAL PRIMARY KEY,
    timestamp TIMESTAMPTZ NOT NULL UNIQUE,
    open      NUMERIC,
    high      NUMERIC,
    low       NUMERIC,
    close     NUMERIC,
    volume    NUMERIC,
    source    TEXT DEFAULT 'unknown'
);

-- ── Indexes ───────────────────────────────────────────────────
CREATE INDEX IF NOT EXISTS idx_gold_prices_ts      ON gold_prices(timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_gold_signals_time   ON gold_signals(signal_time DESC);
CREATE INDEX IF NOT EXISTS idx_gold_signals_status ON gold_signals(order_status);
CREATE INDEX IF NOT EXISTS idx_gold_signals_ch     ON gold_signals(channel_id);

-- ── Auto-update updated_at ────────────────────────────────────
CREATE OR REPLACE FUNCTION set_updated_at()
RETURNS TRIGGER AS $$
BEGIN NEW.updated_at = NOW(); RETURN NEW; END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_gold_signals_updated ON gold_signals;
CREATE TRIGGER trg_gold_signals_updated
    BEFORE UPDATE ON gold_signals
    FOR EACH ROW EXECUTE FUNCTION set_updated_at();
