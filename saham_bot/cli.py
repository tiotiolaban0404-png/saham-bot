"""CLI - antarmuka pengguna (terminal) untuk Stock Bot + Email Pipeline.

Mode yang tersedia:
  program_saham.py daftar [path]          - analisis semua emiten
  program_saham.py daftar --file path     - pakai watchlist lain
  program_saham.py daftar-sepakat k1 k2 ..- hanya kode yang dipilih
  program_saham.py interaktif [path]      - shell sederhana
  program_saham.py sched [hh mm]          - sekali jalan (untuk crontab)
  program_saham.py letter --dry-run       - siapkan surat lamaran WFH
  python -m saham_bot                     - jalankan (default: interaktif)

Env yang dipakai:
  TELEGRAM_TOKEN, TELEGRAM_CHAT_ID
  EMAIL_SMTP_HOST, EMAIL_SMTP_PORT, EMAIL_SMTP_USER, EMAIL_SMTP_PASS
  EMAIL_FROM, EMAIL_TO, EMAIL_SUBJECT
  EMAIL_IMAP_HOST, EMAIL_IMAP_PORT, EMAIL_IMAP_USER, EMAIL_IMAP_PASS
  EMAIL_IMAP_FOLDER, EMAIL_IMAP_DAYS, EMAIL_IMAP_MATCH_FROM
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

from saham_bot import analysis, mail, telegram
from saham_bot.config import config as app_config


# ---------- baca & kirim daftar ============
def jalankan_daftar(tickers, kirim_telegram=False):
    for tk in tickers:
        print()
        print("=" * 62)
        tampil(analysis.analisis(tk))
        if kirim_telegram:
            data = analysis.analisis(tk)
            telegram.kirim(app_config.telegram_token, app_config.telegram_chat_id, data)


def tampil(data):
    if "error" in data:
        print("\nGAGAL: " + data["error"])
        return

    if data.get("harga") is None:
        print("\nGAGAL: " + data.get("error", "Data tidak tersedia."))
        print("  Nama   : " + str(data.get("nama", "Tidak diketahui")))
        print("  Sektor : " + str(data.get("sektor", "Tidak diketahui")))
        print("  Sinyal : " + data.get("rekom", "WAIT"))
        return

    print()
    print("-" * 62)
    print("  EMPITEN :", data["ticker"], "|", data["nama"])
    print("  Sektor  :", data.get("sektor", "Tidak diketahui"))
    print("-" * 62)
    print("  Harga    : Rp " + analysis.fmt(data["harga"]))
    print("  RSI14    : " + analysis.fmt(data["rsi"]))
    print("  EMA20/50 : " + analysis.fmt(data["ema20"]) + " / " + analysis.fmt(data["ema50"]))
    print("  MACD     : " + analysis.fmt(data["macd"]) + " | Signal "
          + analysis.fmt(data["sig"]) + " | Hist " + analysis.fmt(data["hist"]))
    print("  Fibonacci:")
    for fk in sorted(data["fib"].keys()):
        print("    0." + str(int(fk * 1000)) + " : " + analysis.fmt(data["fib"][fk]))
    if data["ema20"] is None or data["ema50"] is None:
        trend = "TIDAK TERSEDIA"
    elif data["ema20"] > data["ema50"]:
        trend = "BULLISH (EMA20 > EMA50)"
    else:
        trend = "BEARISH (EMA20 < EMA50)"
    print("  Tren     : " + trend)
    print("  Sinyal   : " + data["rekom"])
    print("  Risk     : Stop Loss Rp " + analysis.fmt(data["harga"] * analysis.STOP_LOSS)
          + " | Target Rp " + analysis.fmt(data["harga"] * analysis.TAKE_PROFIT))

    if data["rekom"].startswith("BUY"):
        print("\n" + telegram.Fore.GREEN + "  Sinyal  : BELI" + telegram.Style.RESET_ALL)
    elif data["rekom"].startswith("SELL"):
        print("\n" + telegram.Fore.RED + "  Sinyal  : JUAL" + telegram.Style.RESET_ALL)
    else:
        print("\n" + telegram.Fore.YELLOW + "  Sinyal  : WAIT" + telegram.Style.RESET_ALL)


# ---------- interaktif shell ----------
def run_interaktif(watchlist_path=None):
    emiten = []
    if watchlist_path:
        emiten = analysis.baca_watchlist(watchlist_path)
        if emiten:
            print("Daftar emiten dari:", watchlist_path, "->", ", ".join(emiten))

    idx = 0
    while True:
        if not emiten:
            cmd = input("\n[Kode emiten] > ").strip()
            if cmd.lower() in ("keluar", "quit"):
                print("Selesai. Selamat berinvestasi!")
                break
            if cmd.lower() == "list":
                print("Daftar: " + (", ".join(emiten) if emiten else "(belum ada daftar)"))
                continue
            emiten = [cmd.upper()]
            idx = 0
        else:
            if idx >= len(emiten):
                idx = 0
            cmd = input("\n[Emiten] %s > " % emiten[idx])
            if cmd.lower() in ("keluar", "quit"):
                print("Selesai. Selamat berinvestasi!")
                return
            if cmd.lower() == "next":
                idx = (idx + 1) % len(emiten)
                continue
            if cmd.lower() == "list":
                print("Daftar: " + ", ".join(emiten))
                continue
            if cmd.lower().startswith("ganti "):
                new_tk = cmd.split(" ", 1)[1].strip().upper()
                if new_tk:
                    emiten[idx] = new_tk
                continue
            if cmd.lower().startswith("nama "):
                parts = cmd.split(" ", 2)
                if len(parts) >= 3:
                    code = parts[1].strip().upper()
                    NAMA_MANUAL = analysis.NAMA_MANUAL
                    NAMA_MANUAL[code] = parts[2]
                    if emiten[idx] != code:
                        emiten[idx] = code
                else:
                    print("Gunakan: nama <kode> <namamerah>")
                continue
            emiten[idx] = cmd.upper()

        tk = emiten[idx]
        data = analysis.analisis(tk)
        tampil(data)
        kirim_telegram(data, tk)
        idx = (idx + 1) % len(emiten) if len(emiten) > 1 else 0


# ---------- sched (one-shot, untuk crontab) ----------
def jalankan_sched(jam=None, menit=None):
    tickers = analysis.baca_watchlist(app_config.watchlist)
    print("=== ANALISIS HARIAN SAHAM (sched) ===")
    print("Emiten dipantau: " + str(len(tickers)))
    print("Mode: sekali jalan, exit setelah selesai")
    print("=" * 62)
    jalankan_daftar(tickers, kirim_telegram=True)
    print("\n✅ Selesai (analisis selesai; notifikasi terkirim bila token+chat_id terisi).")
    return 0


# ---------- kirim telegram (bila dikonfigurasi) ----------
def kirim_telegram(data, ticker):
    token = os.getenv("TELEGRAM_TOKEN", "")
    chat_id = os.getenv("TELEGRAM_CHAT_ID", "")
    if not token or not chat_id:
        return
    try:
        import requests as _req

        nm = data.get("nama", "Tidak diketahui")
        if data.get("harga") is None:
            pesan = (
                "🤖 *ASISTEN SAHAM* \n"
                "🏢 *Perusahaan:* " + nm + " (" + ticker + ")" + "\n"
                "⚠️ *Status:* Harga belum tersedia (Yahoo Finance)." + "\n"
                "🔍 *Sinyal:* " + data.get("rekom", "WAIT")
            )
        else:
            rs = "BULLISH (EMA20 > EMA50)" if (
                data["ema20"] is not None and data["ema50"] is not None
                and data["ema20"] > data["ema50"]) else "TIDAK TERSEDIA"
            pesan = (
                "🤖 *ASISTEN SAHAM* \n"
                "🏢 *Perusahaan:* " + nm + " (" + ticker + ")" + "\n"
                "💵 *Harga Saat Ini:* Rp " + analysis.fmt(data["harga"]) + "\n"
                "📊 *Indikator RSI-14:* " + analysis.fmt(data["rsi"]) + "\n"
                "📈 *Status Tren:* " + rs + "\n"
                "🎯 *Sinyal Utama:* " + data["rekom"] + "\n"
                "🛑 Stop Loss (5%): Rp " + analysis.fmt(data["harga"] * analysis.STOP_LOSS) + "\n"
                "🎯 Target (10%): Rp " + analysis.fmt(data["harga"] * analysis.TAKE_PROFIT)
            )
        url = "https://api.telegram.org/bot" + token + "/sendMessage"
        payload = {"chat_id": chat_id, "text": pesan, "parse_mode": "Markdown"}
        resp = _req.post(url, json=payload)
        if resp.status_code == 200:
            print(Fore.GREEN + "[SUKSES] Kirim Telegram." + Style.RESET_ALL)
        else:
            print(Fore.RED + "[GAGAL] Telegram: HTTP " + str(resp.status_code) + Style.RESET_ALL)
    except Exception as e:
        print(Fore.RED + "[GAGAL] Telegram: " + str(e) + Style.RESET_ALL)


# ---------- dispatch utama ----------
def main(argv=None):
    args = sys.argv[1:] if argv is None else argv

    if not args:
        run_interaktif()
        return 0

    # legacy: program_saham.py daftar [path]
    if args[0] == "daftar":
        if len(args) >= 3 and args[1] == "--file":
            path = args[2]
        else:
            path = args[1] if len(args) > 1 else None
        jalankan_daftar(analysis.baca_watchlist(path or app_config.watchlist))
        return 0

    if args[0] == "daftar-sepakat":
        tickers = args[1:]
        if not tickers:
            print("Gunakan: python program_saham.py daftar-sepakat <kode1> <kode2> ...")
            return 0
        jalankan_daftar(tickers)
        return 0

    if args[0] == "interaktif":
        path = args[1] if len(args) > 1 else None
        run_interaktif(path)
        return 0

    if args[0] == "sched":
        # sched [hh mm] -> sekali jalan
        jalankan_sched()
        return 0

    if args[0] == "letter":
        dry = "--dry-run" in args
        cfg = app_config
        ok, pesan = mail.kirim_letter(
            letter_path=Path(__file__).resolve().parent.parent / "lamaran_wfh.txt",
            smtp_host=cfg.smtp_host,
            smtp_port=cfg.smtp_port,
            smtp_user=cfg.smtp_user,
            smtp_pass=cfg.smtp_pass,
            smtp_use_tls=cfg.smtp_use_tls,
            frm=cfg.smtp_from,
            to=cfg.smtp_to,
            subject=cfg.smtp_subject,
            dry_run=dry,
        )
        print(pesan)
        return 0 if ok else 1

    # default
    run_interaktif()
    return 0


if __name__ == "__main__":
    sys.exit(main())
