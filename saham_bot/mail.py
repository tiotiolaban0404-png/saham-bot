"""Email pipeline - kirim & baca email (SMTP/IMAP) + surat lamaran.

Modul ini fokus ke "email pipeline":
  - SMTP: kirim laporan saham / surat lamaran
  - IMAP: baca inbox, ekstrak kode emiten, kirim reply balasan
  - Surat lamaran WFH: kirim via SMTP
"""

from __future__ import annotations

import re
import smtplib
from datetime import date, timedelta
from email import policy
from email import message_from_bytes
from email.utils import getaddresses
from pathlib import Path

import pandas as pd
import pandas_ta as ta

from . import analysis
from .config import Config

config = Config()


def kirim_email(host, port, user, password, use_tls, frm, to, subject, body):
    """Kirim surat via SMTP. Return (berhasil: bool, pesan: str)."""
    from email.message import EmailMessage

    em = EmailMessage()
    em["From"] = frm
    em["To"] = to
    em["Subject"] = subject
    em.set_content(body)

    try:
        with smtplib.SMTP(host, port, timeout=30) as server:
            if use_tls:
                server.starttls()
            if user and password:
                server.login(user, password)
            server.send_message(em)
        return True, "Kirim sukses"
    except Exception as e:
        return False, "Gagal kirim: " + str(e)


def _decode_header(val) -> str:
    from email.header import decode_header, make_header

    return str(make_header(decode_header(val)))


def baca_unread_imap(host, port, user, password, folder="INBOX", days: int = 1, match_from: str | None = None):
    """Kembalikan daftar unread email (opsional filter dari alamat) dari IMAP."""
    import imaplib

    last = date.today() - timedelta(days=max(0, int(days)))
    since = last.strftime("%d-%b-%Y")

    imap = imaplib.IMAP4_SSL(host, port, timeout=30)
    typ, _ = imap.login(user, password)
    if typ != "OK":
        return []
    typ, _ = imap.select(folder, readonly=True)
    if typ != "OK":
        imap.logout()
        return []

    typ, data = imap.search(None, "UNSEEN", "SINCE", since)
    ids = data[0].split() if typ == "OK" else []

    results = []
    for mid in ids:
        typ, dat = imap.fetch(mid, "(RFC822)")
        if typ != "OK" or not dat or not dat[0]:
            continue
        raw = dat[0][1]
        msg = message_from_bytes(raw, policy=policy.default)
        frm = _decode_header(msg.get("From")) or "?"
        subj = _decode_header(msg.get("Subject")) or "(no subject)"
        if match_from:
            sendr = frm.split(">")[0].strip().lower()
            if sendr != match_from.lower():
                continue
        results.append({
            "mid": mid,
            "from": frm,
            "subject": subj,
            "date": _decode_header(msg.get("Date")) or "",
            "raw": raw,
        })
    imap.logout()
    return results


def parse_eml(raw_bytes: bytes) -> dict:
    """Parse raw email -> dict (from/subject/body/codes)."""
    msg = message_from_bytes(raw_bytes, policy=policy.default)
    head = {
        "from": _decode_header(msg.get("From")) or "",
        "to": _decode_header(msg.get("To")) or "",
        "subject": _decode_header(msg.get("Subject")) or "",
        "date": _decode_header(msg.get("Date")) or "",
    }
    body = _body_text(msg)
    body = re.sub(r"(?is)<[^>]+>", " ", body)
    body = re.sub(r"\s+", " ", body).strip()
    codes = ekstrak_kode(body + " " + head["subject"], codeset=_codeset_watchlist())
    return {"from": head["from"], "to": head["to"], "subject": head["subject"],
            "date": head["date"], "body": body, "codes": codes}


def _codeset_watchlist() -> set:
    """Kumpulkan kode saham dari watchlist (built-in)."""
    codes = set()
    w = config.watchlist
    try:
        for ln in w.read_text(encoding="utf-8").splitlines():
            ln = ln.strip()
            if ln and not ln.startswith("#") and not ln.startswith("["):
                codes.add(ln.upper())
    except Exception:
        pass
    return codes


def ekstrak_kode(text: str, codeset: set | None = None) -> list[str]:
    if codeset is None:
        codeset = _codeset_watchlist()
    tokens = re.findall(r"\b([A-Z0-9]{1,6}\.[A-Z0-9]{2}(?:\.[A-Z0-9]{2})?)\b", text.upper())
    seen = set()
    out = []
    for t in tokens:
        if t in codeset and t not in seen:
            seen.add(t)
            out.append(t)
    return out


def _body_text(msg) -> str:
    if msg.is_multipart():
        for part in msg.walk():
            if part.get_content_type() == "text/plain":
                payload = part.get_payload(decode=True)
                if isinstance(payload, bytes):
                    return payload.decode("utf-8", "replace")
                return str(payload or "")
    else:
        payload = msg.get_payload(decode=True)
        if isinstance(payload, bytes):
            return payload.decode("utf-8", "replace")
        return str(payload or "")
    return ""


# ============ Surat lamaran (WFH) ============
def kirim_letter(
    letter_path,
    smtp_host: str,
    smtp_port: int,
    smtp_user: str,
    smtp_pass: str,
    smtp_use_tls: bool,
    frm: str,
    to: str,
    subject: str,
    dry_run: bool = False,
):
    """Kirim file surat (WFH) via SMTP. Return (berhasil, pesan)."""
    try:
        body = Path(letter_path).read_text(encoding="utf-8")
    except Exception as e:
        return False, "Gagal baca file surat: " + str(e)

    # placeholder opsional
    body = body.replace("{NAMA}", "[NAMA LENGKAP]")
    body = body.replace("{POSISI}", "[POSISI LAMARAN]")
    body = body.replace("{PERUSAHAAN}", "[NAMA PERUSAHAAN]")
    body = body.replace("{TANGGAL}", date.today().strftime("%d %b %Y"))

    from email.message import EmailMessage

    em = EmailMessage()
    em["From"] = frm
    em["To"] = to
    em["Subject"] = subject
    em.set_content(body)

    if dry_run:
        out = Path("laporan_lamaran_") / (date.today().strftime("%Y%m%d") + ".eml")
        out.parent.mkdir(exist_ok=True)
        out.write_text(em.as_string(), encoding="utf-8")
        return True, f"[DRY-RUN] Surat ditulis -> {out}"

    try:
        with smtplib.SMTP(smtp_host, smtp_port, timeout=30) as server:
            if smtp_use_tls:
                server.starttls()
            if smtp_user and smtp_pass:
                server.login(smtp_user, smtp_pass)
            server.send_message(em)
        return True, "Surat lamaran terkirim"
    except Exception as e:
        return False, "Gagal kirim surat: " + str(e)
