"""Database layer - SQLite (sederhana) + penanganan langganan user.

Langkah:
  1. python3 saham_bot/db.py init
  2. python3 saham_bot/db.py register <chat_id> [username]
  3. python3 saham_bot/db.py subscribe <chat_id> pro 30
"""

from __future__ import annotations

import os
import sqlite3
from datetime import datetime, timedelta
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
DEFAULT_DB = os.getenv("SAHAM_DB", str(BASE_DIR / "alerts.db"))

SCHEMA = """
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
CREATE INDEX IF NOT EXISTS idx_users_identifier ON users(identifier);
CREATE INDEX IF NOT EXISTS idx_users_status ON users(status);

CREATE TABLE IF NOT EXISTS alerts (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id    INTEGER NOT NULL,
    ticker     TEXT NOT NULL,
    signal     TEXT NOT NULL,
    price      REAL,
    sent_at    TEXT NOT NULL DEFAULT (datetime('now')),
    FOREIGN KEY (user_id) REFERENCES users(id)
);
CREATE INDEX IF NOT EXISTS idx_alerts_user ON alerts(user_id);

CREATE TABLE IF NOT EXISTS plans (
    id   TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    price_rp INTEGER NOT NULL DEFAULT 0,
    period_days INTEGER NOT NULL DEFAULT 30,
    features TEXT NOT NULL DEFAULT ''
);
INSERT OR IGNORE INTO plans(id, name, price_rp, period_days, features) VALUES
('free', 'Free', 0, 1, '10 emiten, 1 Telegram alert/hari'),
('pro', 'Pro', 25000, 30, '50 emiten, multi-notif, tanpa batas');
"""


def now_iso() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def get_conn(db_path: str | Path | None = None):
    path = Path(db_path or os.getenv("SAHAM_DB", DEFAULT_DB))
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db(db_path: str | Path | None = None):
    conn = get_conn(db_path)
    conn.executescript(SCHEMA)
    conn.commit()
    return conn


def upsert_user(conn, chat_id: str, username: str | None = None) -> sqlite3.Row:
    """Tambah / perbarui user berdasarkan chat_id. Kembalikan baris user."""
    now = now_iso()
    conn.execute(
        """
        INSERT INTO users (identifier, username, status, plan, start_date, end_date, is_active, updated_at)
        VALUES (:id, :uname, 'active', 'free', :start, NULL, 1, :updated)
        ON CONFLICT(identifier) DO UPDATE SET
            username = COALESCE(excluded.username, users.username),
            status = 'active',
            is_active = 1,
            start_date = COALESCE(excluded.start_date, start_date),
            end_date = excluded.end_date,
            updated_at = :updated
        """,
        {"id": chat_id, "uname": username, "start": now, "updated": now},
    )
    conn.commit()
    return conn.execute("SELECT * FROM users WHERE identifier=?", (chat_id,)).fetchone()


def set_subscription(conn, chat_id: str, plan: str, period_days: int) -> sqlite3.Row:
    """Atur langganan: plan + masa aktif (start -> end)."""
    now = now_iso()
    end = (datetime.strptime(now, "%Y-%m-%d %H:%M:%S") + timedelta(days=period_days)).strftime(
        "%Y-%m-%d %H:%M:%S"
    )
    conn.execute(
        """
        INSERT INTO users (identifier, username, status, plan, start_date, end_date, is_active, updated_at)
        VALUES (:id, :uname, 'active', :plan, :start, :end, 1, :updated)
        ON CONFLICT(identifier) DO UPDATE SET
            username = COALESCE(excluded.username, users.username),
            plan = excluded.plan,
            status = 'active',
            is_active = 1,
            start_date = excluded.start_date,
            end_date = excluded.end_date,
            updated_at = :updated
        """,
        {
            "id": chat_id,
            "uname": None,
            "plan": plan,
            "start": now,
            "end": end,
            "updated": now,
        },
    )
    conn.commit()
    return conn.execute("SELECT * FROM users WHERE identifier=?", (chat_id,)).fetchone()


def set_status(conn, chat_id: str, status: str, end_date=None) -> sqlite3.Row | None:
    """Batalkan/pause langganan."""
    now = now_iso()
    conn.execute(
        """
        UPDATE users SET status=?, is_active=?,
            start_date = COALESCE(start_date, ?),
            end_date = ?,
            updated_at = ?
        WHERE identifier=?
        """,
        (status, 0, now, end_date or now, now, chat_id),
    )
    conn.commit()
    return conn.execute("SELECT * FROM users WHERE identifier=?", (chat_id,)).fetchone()


def get_user(conn, chat_id: str) -> sqlite3.Row | None:
    return conn.execute("SELECT * FROM users WHERE identifier=?", (chat_id,)).fetchone()


def get_active_users(conn) -> list:
    return conn.execute(
        """
        SELECT u.*, COALESCE(p.price_rp, 0) AS plan_price
        FROM users u
        LEFT JOIN plans p ON p.id = u.plan
        WHERE u.is_active = 1 AND u.status = 'active'
          AND (u.end_date IS NULL OR u.end_date >= ?)
        ORDER BY u.created_at
        """,
        (now_iso(),),
    ).fetchall()


def log_alert(conn, user_id: int, ticker: str, signal: str, price: float | None = None):
    conn.execute(
        "INSERT INTO alerts (user_id, ticker, signal, price, sent_at) VALUES (?, ?, ?, ?, ?)",
        (user_id, ticker, signal, price, now_iso()),
    )
    conn.commit()


def end_period(conn, user_id: int, end_date=None):
    now = now_iso()
    conn.execute(
        "UPDATE users SET end_date=?, updated_at=? WHERE id=?",
        (end_date or now, now, user_id),
    )
    conn.commit()


# ---- CLI demo ----
def main():
    import argparse

    p = argparse.ArgumentParser(description="Database layer saham-bot")
    sub = p.add_subparsers(dest="cmd", required=True)

    sub.add_parser("init")
    p_register = sub.add_parser("register")
    p_register.add_argument("chat_id")
    p_register.add_argument("username", nargs="?", default=None)
    p_subscribe = sub.add_parser("subscribe")
    p_subscribe.add_argument("chat_id")
    p_subscribe.add_argument("plan")
    p_subscribe.add_argument("days", type=int, default=30)
    p_cancel = sub.add_parser("cancel")
    p_cancel.add_argument("chat_id")
    sub.add_parser("list-users")
    sub.add_parser("renew")

    args = p.parse_args()
    conn = init_db()

    if args.cmd == "init":
        print("✅ database siap:", get_conn().execute("SELECT 1").fetchone())
    elif args.cmd == "register":
        r = upsert_user(conn, args.chat_id, args.username)
        print("✅ user terdaftar:", r["identifier"], r["plan"], r["start_date"])
    elif args.cmd == "subscribe":
        r = set_subscription(conn, args.chat_id, args.plan, args.days)
        print("✅ langganan:", r["identifier"], r["plan"], r["end_date"])
    elif args.cmd == "cancel":
        set_status(conn, args.chat_id, "cancelled")
        print("✅ user dibatalkan")
    elif args.cmd == "list-users":
        for u in conn.execute(
            "SELECT identifier, username, plan, status, is_active, start_date, end_date "
            "FROM users ORDER BY created_at"
        ):
            print(dict(u))
    elif args.cmd == "renew":
        for u in get_active_users(conn):
            end = u["end_date"]
            if end and datetime.strptime(end, "%Y-%m-%d %H:%M:%S") < datetime.now():
                set_status(conn, str(u["identifier"]), "paused")
                print("⏸️  pause:", u["identifier"], "expired")
        print("✅ renewal selesai")


if __name__ == "__main__":
    main()
