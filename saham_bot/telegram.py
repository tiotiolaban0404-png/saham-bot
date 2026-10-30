"""Pengiriman notifikasi ke Telegram.

Menerima (token, chat_id, data) sebagai param -> tidak menganggap env di fungsi
ini, supaya mudah diuji & dipakai oleh cron (env di luar fungsi).
"""

from __future__ import annotations

import os
from pathlib import Path

import requests

from colorama import Fore, Style

from .analysis import fmt
from .config import config

# Status baca (bisa diubah nanti)
STOP_LOSS = 0.95
TAKE_PROFIT = 1.10


def kirim(token: str, chat_id: str, data: dict) -> None:
    """Kirim laporan saham lewat Telegram UI Markdown."""
    if not token or not chat_id:
        return
    msg = _bungkus_pesan(data)
    url = "https://api.telegram.org/bot" + token + "/sendMessage"
    payload = {"chat_id": chat_id, "text": msg, "parse_mode": "Markdown"}
    try:
        resp = requests.post(url, json=payload, timeout=20)
        if resp.status_code == 200:
            print("[SUKSES] Kirim ke Telegram.")
        else:
            print(f"[GAGAL] Telegram API: HTTP {resp.status_code}")
    except Exception as e:
        print("[GAGAL] Telegram: " + str(e))


def _bungkus_pesan(data: dict) -> str:
    if data.get("harga") is None:
        return (
            "🤖 *ASISTEN SAHAM*\n"
            "🏢 *Perusahaan:* " + data.get("nama", "Tidak diketahui") +
            " (" + data.get("ticker", "") + ")\n"
            "⚠️ *Status:* Harga belum tersedia (Yahoo Finance).\n"
            "🔍 *Sinyal:* " + data.get("rekom", "WAIT")
        )

    if data["ema20"] is None or data["ema50"] is None:
        trend = "TIDAK TERSEDIA"
    elif data["ema20"] > data["ema50"]:
        trend = "BULLISH (EMA20 > EMA50)"
    else:
        trend = "BEARISH (EMA20 < EMA50)"
    return (
        "🤖 *ASISTEN SAHAM*\n"
        "🏢 *Perusahaan:* " + data.get("nama", "Tidak diketahui") +
        " (" + data.get("ticker", "") + ")\n"
        "💵 *Harga Saat Ini:* Rp " + fmt(data["harga"]) + "\n"
        "📊 *Indikator RSI-14:* " + fmt(data["rsi"]) + "\n"
        "📈 *Status Tren:* " + trend + "\n"
        "🎯 *Sinyal Utama:* " + data["rekom"] + "\n"
        "🛑 Stop Loss (5%): Rp " + fmt(data["harga"] * STOP_LOSS) + "\n"
        "🎯 Target (10%): Rp " + fmt(data["harga"] * TAKE_PROFIT)
    )
