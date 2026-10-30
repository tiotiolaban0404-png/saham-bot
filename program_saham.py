#!/usr/bin/env python3
"""
LAUNCHER legacy -> mengalihkan ke paket baru (saham_bot).

Pemakaian lama yang masih berlaku:
  python program_saham.py daftar [path]
  python program_saham.py daftar-sepakat k1 k2 ...
  python program_saham.py interaktif [path]
  python program_saham.py sched [hh mm]
  python program_saham.py letter --dry-run
"""

import sys

from saham_bot import cli

# Daemon mode seperti yang diminta: JALAKAN SEMUA, lalu exit (tidak looping).
# Cron sudah menjadwalkan waktu, jadi CLI langsung mengerjakan sekarang.
def main(argv=None):
    if argv is None:
        argv = sys.argv[1:]
    if not argv:
        argv = ["interaktif"]
    return cli.main(argv)


if __name__ == "__main__":
    sys.exit(main())
