"""Analisis teknis emiten - harga + indikator + sinyal.
Direpresentasikan ulang menjadi paket bersih (saham_bot), tetapi
logika & output tetap sama persis seperti program_saham.py sebelumnya.
"""

from __future__ import annotations

import os
import subprocess

import pandas as pd
import pandas_ta as ta
from colorama import Fore, Style

from .config import config

# --------------------------- KONFIGURASI -------------------------
RSI_BUY = 35
RSI_SELL = 70
EMA20_LEN = 20
EMA50_LEN = 50
MACD_FAST = 12
MACD_SLOW = 26
MACD_SIGNAL = 9
STOP_LOSS = 0.95
TAKE_PROFIT = 1.10
NEAR_FIBO_TOL = 0.02
FIB_LEVELS = (0.382, 0.500, 0.618, 0.786)

NAMA_MANUAL = {}

# Cache daftar emiten (di-load sekali, dari watchlist)
_WATCHLIST = None


# --------------------------- BANTUAN -------------------------
def ambil_nama(ticker: str) -> str | None:
    """Nama emiten dari Yahoo. Return None bila gagal."""
    try:
        import yfinance as yf

        return yf.Ticker(ticker).info.get("longName")
    except Exception:
        return None


def ambil_sektor(ticker: str) -> str:
    try:
        import yfinance as yf

        return yf.Ticker(ticker).info.get("sector") or "Tidak diketahui"
    except Exception:
        return "Tidak diketahui"


def _num(last_row: pd.Series, col: str):
    v = last_row.get(col)
    if v is None or pd.isna(v):
        return None
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


def fmt(x, digits: int = 2):
    if x is None:
        return "N/A"
    return f"{x:.{digits}f}"


def clear_screen() -> None:
    subprocess.call(["cls"] if os.name == "nt" else ["clear"])


def ambil_nama_ttl(ticker: str, override_nama: str | None = None) -> str:
    """Nama emiten: manual > diskripsi > Yahoo > default."""
    return (override_nama or NAMA_MANUAL.get(ticker) or ambil_nama(ticker) or "Tidak diketahui")


def baca_watchlist(path) -> list[str]:
    """Baca daftar emiten dari file (satu kode per baris, # diabaikan)."""
    emiten = []
    try:
        with open(path, encoding="utf-8") as fh:
            for baris in fh:
                baris = baris.strip()
                if not baris or baris.startswith("#"):
                    continue
                emiten.append(baris.split("#")[0].strip().split()[0].upper())
    except FileNotFoundError:
        print("Tidak dapat baca file watchlist:", path)
    return emiten


def get_watchlist() -> list[str]:
    """Load list emiten (caching). Default dari config.ini atau watchlist_saham.txt."""
    global _WATCHLIST
    if _WATCHLIST is None:
        _WATCHLIST = baca_watchlist(config.watchlist)
    return _WATCHLIST


# --------------------------- ANALISIS -------------------------
def analisis(ticker: str, override_nama: str | None = None):
    ticker = ticker.strip().upper()
    try:
        import yfinance as yf

        info = yf.Ticker(ticker)
        df = info.history(period="6mo", interval="1d")
    except Exception:
        return {"error": "Gagal memuat data emiten " + ticker}

    if df is None or df.empty or len(df) < 50:
        return {
            "ticker": ticker,
            "status": "data_tidak_tersedia",
            "nama": ambil_nama_ttl(ticker, override_nama),
            "rsi": None,
            "ema20": None,
            "ema50": None,
            "macd": None,
            "sig": None,
            "hist": None,
            "cross_up": False,
            "cross_down": False,
            "near_fibo": False,
            "fib": {},
            "rekom": "WAIT | Data harga belum tersedia",
            "error": "Data " + ticker + " tidak cukup / tidak ditemukan.",
        }

    try:
        df = df.dropna(subset=["Close"]).copy()
        if df.empty or len(df) < 50:
            return {
                "ticker": ticker,
                "status": "data_tidak_tersedia",
                "nama": ambil_nama_ttl(ticker, override_nama),
                "rsi": None,
                "ema20": None,
                "ema50": None,
                "macd": None,
                "sig": None,
                "hist": None,
                "cross_up": False,
                "cross_down": False,
                "near_fibo": False,
                "fib": {},
                "rekom": "WAIT | Data harga belum tersedia",
                "error": "Data " + ticker + " tidak cukup / tidak ditemukan.",
            }

        df["EMA_20"] = ta.ema(df["Close"], length=EMA20_LEN)
        df["EMA_50"] = ta.ema(df["Close"], length=EMA50_LEN)
        df["RSI"] = ta.rsi(df["Close"], length=14)
        m = ta.macd(df["Close"], fast=MACD_FAST, slow=MACD_SLOW, signal=MACD_SIGNAL)
        df["MACD"] = m["MACD_12_26_9"]
        df["MACD_Signal"] = m["MACDs_12_26_9"]
        df["MACD_Hist"] = m["MACDh_12_26_9"]

        high_max = float(df["High"].max())
        low_min = float(df["Low"].min())
        diff = high_max - low_min
        fib = {f: high_max - (f * diff) for f in FIB_LEVELS}

        cur = df.iloc[-1]
        prev = df.iloc[-2]

        harga = _num(cur, "Close")
        if harga is None:
            return {"error": "Harga tidak tersedia."}
        rsi = _num(cur, "RSI")
        ema20 = _num(cur, "EMA_20")
        ema50 = _num(cur, "EMA_50")
        macd = _num(cur, "MACD")
        sig = _num(cur, "MACD_Signal")
        hist = _num(cur, "MACD_Hist")

        prev_macd = _num(prev, "MACD")
        prev_sig = _num(prev, "MACD_Signal")

        cross_up = (prev_macd <= prev_sig) and (macd > sig)
        cross_down = (prev_macd >= prev_sig) and (macd < sig)

        near_fibo = False
        for fv in fib.values():
            if fv != 0 and abs(harga - fv) / fv <= NEAR_FIBO_TOL:
                near_fibo = True
                break

        if rsi is not None:
            if rsi >= RSI_SELL:
                rekom = "SELL | Overbought"
            elif rsi <= RSI_BUY:
                rekom = "BUY | Oversold"
            else:
                rekom = ""
        else:
            rekom = ""

        if rekom == "":
            if cross_up or (hist is not None and hist > 0 and near_fibo):
                rekom = "BUY | Momentum naik / Fibonacci support"
            elif cross_down or (ema20 is not None and ema50 is not None
                                and ema20 < ema50 and hist is not None and hist < 0):
                rekom = "SELL | Dead cross / tren melemah"
            else:
                rekom = "WAIT | Belum ada sinyal kuat"

        return {
            "ticker": ticker,
            "nama": ambil_nama_ttl(ticker, override_nama),
            "sektor": ambil_sektor(ticker),
            "harga": harga,
            "rsi": rsi,
            "ema20": ema20,
            "ema50": ema50,
            "macd": macd,
            "sig": sig,
            "hist": hist,
            "cross_up": cross_up,
            "cross_down": cross_down,
            "near_fibo": near_fibo,
            "fib": fib,
            "rekom": rekom,
        }
    except Exception as e:
        return {"error": "Hitung indikator gagal: " + str(e)}
