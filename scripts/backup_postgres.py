"""Backup PostgreSQL via pg_dump (Fase C5)."""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from urllib.parse import unquote, urlparse

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent
load_dotenv(ROOT / ".env")


def _parse_db_url(url: str) -> dict[str, str]:
    p = urlparse(url)
    return {
        "host": p.hostname or "localhost",
        "port": str(p.port or 5432),
        "user": unquote(p.username or ""),
        "password": unquote(p.password or ""),
        "dbname": (p.path or "/").lstrip("/"),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Backup PostgreSQL (pg_dump)")
    parser.add_argument("--output", "-o", help="Arquivo de saida (.dump ou .sql)")
    args = parser.parse_args()

    url = os.environ.get("DATABASE_URL", "").strip()
    if not url.startswith("postgresql"):
        print("DATABASE_URL PostgreSQL nao configurado.")
        return 1

    cfg = _parse_db_url(url)
    out_dir = ROOT / "backups"
    out_dir.mkdir(exist_ok=True)
    out_path = Path(args.output) if args.output else out_dir / f"backup_{datetime.now():%Y%m%d_%H%M%S}.dump"

    env = os.environ.copy()
    if cfg["password"]:
        env["PGPASSWORD"] = cfg["password"]

    cmd = [
        "pg_dump",
        "-h",
        cfg["host"],
        "-p",
        cfg["port"],
        "-U",
        cfg["user"],
        "-F",
        "c",
        "-f",
        str(out_path),
        cfg["dbname"],
    ]

    try:
        subprocess.run(cmd, check=True, env=env, capture_output=True, text=True)
    except FileNotFoundError:
        print("pg_dump nao encontrado. Instale PostgreSQL client tools.")
        return 1
    except subprocess.CalledProcessError as exc:
        print(f"pg_dump falhou: {exc.stderr or exc}")
        return 1

    print(f"Backup OK: {out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
