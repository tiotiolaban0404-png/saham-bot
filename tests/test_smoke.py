"""Smoke test - verifikasi paket saham_bot dapat diimpor dan berjalan.

Jalankan:
    cd saham-bot
    python3 -m unittest discover -s tests -v
"""

import os
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import saham_bot  # noqa: E402
import saham_bot.cli  # noqa: E402
from saham_bot import analysis, config, mail, telegram  # noqa: E402


class TestPackage(unittest.TestCase):
    def test_package_version(self):
        self.assertIsNotNone(saham_bot.__version__)
        self.assertTrue(saham_bot.__version__ >= "1.0.0")

    def test_public_api(self):
        for name in ["analysis", "config", "telegram", "mail", "cli"]:
            self.assertTrue(hasattr(saham_bot, name), f"missing {name}")


class TestConfig(unittest.TestCase):
    def test_watchlist_exists(self):
        self.assertTrue(config.Config().watchlist.exists())

    def test_uses_config_file(self):
        old = os.environ.get("SAHAM_CONFIG")
        os.environ["SAHAM_CONFIG"] = str(Path(__file__).resolve().parent / "config.ini.example")
        try:
            self.assertEqual(config.Config().watchlist.name, "watchlist_saham.txt")
        finally:
            if old is None:
                os.environ.pop("SAHAM_CONFIG", None)
            else:
                os.environ["SAHAM_CONFIG"] = old


class TestAnalysis(unittest.TestCase):
    def test_get_watchlist_returns_items(self):
        tickers = analysis.get_watchlist()
        self.assertGreaterEqual(len(tickers), 1)

    def test_ambil_nama_ttl(self):
        self.assertIsInstance(analysis.ambil_nama_ttl("BBCA.JK"), str)


class TestTelegram(unittest.TestCase):
    def test_kirim_returns_when_no_token(self):
        # Harus gagal aman tanpa token, bukan raise
        telegram.kirim("", "chat-id", {})
        telegram.kirim("token", "", {})
        telegram.kirim("", "", {})

    def test_mail_kirim_letter_reads_path(self):
        ok, msg = mail.kirim_letter(
            letter_path=Path(__file__).resolve().parent.parent / "lamaran_wfh.txt",
            smtp_host="smtp.gmail.com",
            smtp_port=587,
            smtp_user="",
            smtp_pass="",
            smtp_use_tls=False,
            frm="a@b.c",
            to="c@d.e",
            subject="Test",
            dry_run=True,
        )
        self.assertTrue(ok)
        self.assertIn("DRY-RUN", msg)


if __name__ == "__main__":
    unittest.main()
