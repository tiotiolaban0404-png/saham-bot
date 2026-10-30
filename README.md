# Stock Bot & Email Pipeline

Alat analisis teknis saham (Indonesia IHSG + Wall Street) beserta email/Telegram
alert otomatis. Dibangun di atas `yfinance`, `pandas`, `pandas_ta`, `colorama` dan
`requests`.

> ⚠️ **Disclaimer:** alat analisis teknikal, bukan rekomendasi keuangan. Semua
> sinyal (BUY/SELL/WAIT) bersifat indikatif; lakukan validasi mandiri sebelum
> bertransaksi atau berinvestasi.

---

## Struktur Folder

```
saham-bot/
├── program_saham.py         # launcher legacy (panggil dari terminal)
├── watchlist_saham.txt      # daftar emiten (satu kode per baris)
├── config.ini.example       # template konfigurasi (salin ke config.ini)
├── requirements.txt         # library Python
├── .gitignore
├── LICENSE
├── saham_bot/               # paket inti
│   ├── __init__.py
│   ├── analysis.py          # analisis teknis (EMA20/50, RSI14, MACD, Fibonacci)
│   ├── config.py            # pembaca config.ini + env
│   ├── telegram.py          # kirim notifikasi Telegram
│   ├── mail.py              # email (SMTP/IMAP) & surat lamaran
│   └── cli.py               # antarmuka terminal
```

---

## Install & Onboard

1. **Install Python package**

   ```bash
   python3 -m venv .venv && source .venv/bin/activate
   pip install -r requirements.txt
   ```

2. **Salin config & isi kredensial**

   ```bash
   cp config.ini.example config.ini
   # edit config.ini: telegram, smtp, report, imap
   ```

   Atau pakai env variabel (lebih aman daripada file):

   ```bash
   export TELEGRAM_TOKEN=...
   export TELEGRAM_CHAT_ID=...
   export EMAIL_SMTP_HOST=smtp.gmail.com
   export EMAIL_SMTP_PORT=587
   export EMAIL_SMTP_USER=a@gmail.com
   export EMAIL_SMTP_PASS=xxxxx
   export EMAIL_FROM=a@gmail.com
   export EMAIL_TO=b@gmail.com
   export EMAIL_IMAP_HOST=imap.gmail.com
   export EMAIL_IMAP_PORT=993
   export EMAIL_IMAP_USER=a@gmail.com
   export EMAIL_IMAP_PASS=xxxxx
   ```

3. **Jalankan**

   ```bash
   python3 program_saham.py daftar        # semua emiten
   python3 program_saham.py daftar-sepakat BBCA.JK BMRI.JK
   python3 program_saham.py interaktif
   python3 program_saham.py sched 08 00   # sekali jalan (untuk crontab)
   python3 program_saham.py letter --dry-run
   python3 program_saham.py letter --send
   ```

---

## Mode Skenario

| Mode | Perintah | Keterangan |
|---|---|---|
| Daftar (semua) | `daftar [path]` | Scan semua emiten di watchlist |
| Pilih kode | `daftar-sepakat k1 k2 ...` | Hanya kode yang dipilih |
| Interaktif | `interaktif [path]` | Shell: ketik kode, `list`, `next`, `ganti <kode>` |
| Sched | `sched [HH MM]` | Satu kali jalan (cron call) |
| Surat WFH | `letter [--dry-run]` | Siapkan/kirim surat lamaran email |

---

## Cron (Laporan Harian)

Contoh cron (08:00 WIB = 01:00 UTC):

```cron
0 1 * * * cd /home/ridho/Downloads/saham-bot && /usr/bin/python3 program_saham.py sched 08 00
```

Env wajib di-set di crontab:

```cron
SHELL=/bin/bash
PATH=/usr/bin:/bin
TELEGRAM_TOKEN=...
TELEGRAM_CHAT_ID=...
EMAIL_SMTP_HOST=smtp.gmail.com
EMAIL_SMTP_PORT=587
EMAIL_SMTP_USER=a@gmail.com
EMAIL_SMTP_PASS=xxxxx
EMAIL_FROM=a@gmail.com
EMAIL_TO=b@gmail.com
EMAIL_IMAP_HOST=imap.gmail.com
EMAIL_IMAP_PORT=993
EMAIL_IMAP_USER=a@gmail.com
EMAIL_IMAP_PASS=xxxxx
```

---

## Fitur Email Pipeline

| Fitur | Kode | Catatan |
|---|---|---|
| Kirim laporan saham | `telegram.kirim(token, chat_id, data)` | 1 pass param |
| Kirim surat lamaran WFH | `program_saham.py letter [--dry-run]` | pakai SMTP dari config |
| Baca inbox (IMAP) | `mail.baca_unread_imap(host, port, user, pass, folder, days, match_from)` | return list dict raw |
| Parse email | `mail.parse_eml(raw)` → {from/subject/body/codes} | deteksi kode saham |
| Reply / kirim balasan | dari kode `mail` | reply ke pengirim |

---

## Konsistensi & Test

Output teknis sama persis dengan `program_saham.py` lama (harga, EMA20/50,
RSI14, MACD, Fibonacci, sinyal BUY/SELL/WAIT). Untuk verifikasi cepat:

```bash
cd saham-bot
python3 -c "import saham_bot; print(saham_bot.__version__)"
python3 program_saham.py letter --dry-run
```

---

## Lisensi & Panduan

- **Lisensi aplikasi**: MIT (lihat file `LICENSE`).
- **Hak cipta**: "Ridho" (2026). Ubah sesuai keinginanmu.
- **Library** yang dipakai (semua permissif, aman dijadikan open-source):
  `yfinance`, `pandas`, `pandas_ta`, `colorama`, `requests`.
- Catatan: jika nanti kamu butuh klausul lebih ketat (contoh: beta, support
  berbayar, atau larangan re-distribusi), ganti license di `LICENSE` saja —
  kode inti nggak perlu diubah.

> ⚠️ Disclaimer: ini alat analisis teknikal, bukan rekomendasi keuangan. Semua
> sinyal (BUY/SELL/WAIT) bersifat indikatif; lakukan validasi mandiri sebelum
> bertransaksi atau berinvestasi.
