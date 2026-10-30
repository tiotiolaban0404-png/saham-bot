"""Konfigurasi aplikasi - dibaca dari config.ini (dan env variabel).

Prioritas nilai (paling tinggi pertama):
  1. env variabel            (SAHAM_* / TELEGRAM_* / EMAIL_*)
  2. baris [section] key     di config.ini
  3. default empiris

Contoh env:
  TELEGRAM_TOKEN=xxx TELEGRAM_CHAT_ID=123
  SMTP_TOKEN=yyy SMTP_CHAT_ID=456 EMAIL_FROM=a@b.c EMAIL_TO=d@e.f
"""

from __future__ import annotations

import configparser
import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent

DEFAULT_WATCHLIST = "watchlist_saham.txt"
DEFAULT_CONFIG_FILE = "config.ini"


def _load_cfg(path: Path | None = None) -> configparser.ConfigParser:
    cp = configparser.ConfigParser()
    p = path or Path(os.getenv("SAHAM_CONFIG", str(BASE_DIR / "config.ini")))
    if p.exists():
        cp.read(p)
    return cp


class Config:
    """Akses konfigurasi bersih, tidak repot menangani raw ConfigParser."""

    def __init__(self, path: Path | None = None):
        self.path = Path(path) if path else Path(
            os.getenv("SAHAM_CONFIG", str(BASE_DIR / "config.ini"))
        )
        self._cfg = _load_cfg(self.path)

    # -- cambang env var umum --
    def get(self, section: str, key: str, default: str = "", env_name: str | None = None) -> str:
        env_name = env_name or f"SAHAM_{section.upper()}_{key.upper()}"
        env_val = os.getenv(env_name)
        if env_val:
            return env_val
        if self._cfg.has_option(section, key):
            return self._cfg.get(section, key).strip()
        return default

    # ---------- saham ----------
    @property
    def watchlist(self) -> Path:
        return Path(self.get("saham", "watchlist", str(BASE_DIR / DEFAULT_WATCHLIST)))

    # ---------- telegram ----------
    @property
    def telegram_token(self) -> str:
        return self.get("telegram", "token", "", "TELEGRAM_TOKEN")

    @property
    def telegram_chat_id(self) -> str:
        return self.get("telegram", "chat_id", "", "TELEGRAM_CHAT_ID")

    # ---------- smtp ----------
    @property
    def smtp_host(self) -> str:
        return self.get("smtp", "host", "", "EMAIL_SMTP_HOST")

    @property
    def smtp_port(self) -> int:
        return int(self.get("smtp", "port", "587", "EMAIL_SMTP_PORT"))

    @property
    def smtp_user(self) -> str:
        return self.get("smtp", "user", "", "EMAIL_SMTP_USER")

    @property
    def smtp_pass(self) -> str:
        return self.get("smtp", "pass", "", "EMAIL_SMTP_PASS")

    @property
    def smtp_use_tls(self) -> bool:
        v = self.get("smtp", "use_tls", "true", "EMAIL_USE_TLS")
        return v.lower() not in ("0", "false", "no")

    @property
    def smtp_from(self) -> str:
        return self.get("report", "from", "", "EMAIL_FROM")

    @property
    def smtp_to(self) -> str:
        return self.get("report", "to", "", "EMAIL_TO")

    @property
    def smtp_subject(self) -> str:
        return self.get("report", "subject", "Laporan Saham {date}", "EMAIL_SUBJECT")

    @property
    def smtp_subject_date(self) -> str:
        import datetime

        return datetime.date.today().strftime("%d %b %Y")

    # ---------- imap ----------
    @property
    def imap_host(self) -> str:
        return self.get("imap", "host", "", "EMAIL_IMAP_HOST")

    @property
    def imap_port(self) -> int:
        return int(self.get("imap", "port", "993", "EMAIL_IMAP_PORT"))

    @property
    def imap_user(self) -> str:
        return self.get("imap", "user", "", "EMAIL_IMAP_USER")

    @property
    def imap_pass(self) -> str:
        return self.get("imap", "pass", "", "EMAIL_IMAP_PASS")

    @property
    def imap_folder(self) -> str:
        return self.get("imap", "folder", "INBOX", "EMAIL_IMAP_FOLDER")

    @property
    def imap_days(self) -> int:
        return int(self.get("imap", "days", "1", "EMAIL_IMAP_DAYS"))

    @property
    def imap_match_from(self) -> str:
        return self.get("imap", "match_from", "", "EMAIL_IMAP_MATCH_FROM")


# Memudahkan import langsung: config = Config()
config = Config()
