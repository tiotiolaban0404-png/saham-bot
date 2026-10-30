-- Schema & seed untuk stock-bot (SQLite)
-- Giral file:  saham_bot/db.py

-- 1. User saranlangganan
CREATE TABLE IF NOT EXISTS users (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    identifier    TEXT UNIQUE NOT NULL,
    username      TEXT,
    status        TEXT NOT NULL DEFAULT 'active',
    plan          TEXT NOT NULL DEFAULT 'free',
    start_date    TEXT NOT NULL DEFAULT (datetime('now')),
    end_date      TEXT,
    is_active     INTEGER NOT NULL DEFAULT 1,
    created_at    TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at    TEXT NOT NULL DEFAULT (datetime('now'))
);
CREATE INDEX idx_users_identifier ON users(identifier);
CREATE INDEX idx_users_status ON users(status);

-- 2. Log notifikasi (alerts) biar bisa audit & rekap
CREATE TABLE alerts (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id    INTEGER NOT NULL,
    ticker     TEXT NOT NULL,
    signal     TEXT NOT NULL,
    price      REAL,
    sent_at    TEXT NOT NULL DEFAULT (datetime('now')),
    FOREIGN KEY (user_id) REFERENCES users(id)
);
CREATE INDEX idx_alerts_user ON alerts(user_id);

-- 3. Daftar plan berlangganan
CREATE TABLE plans (
    id   TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    price_rp INTEGER NOT NULL DEFAULT 0,
    period_days INTEGER NOT NULL DEFAULT 30,
    features TEXT NOT NULL DEFAULT ''
);

INSERT OR IGNORE INTO plans(id, name, price_rp, period_days, features) VALUES
('free',  'Free',   0, 1,  '10 emiten, 1 Telegram alert/hari'),
('pro',   'Pro',    25000, 30, '50 emiten, multi-notif, tanpa batas');
