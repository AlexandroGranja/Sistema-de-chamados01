"""Valida sintaxe do docker-compose.stack.yml (Fase C5)."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
COMPOSE = ROOT / "docker-compose.stack.yml"


def main() -> int:
    if not COMPOSE.is_file():
        print(f"Arquivo ausente: {COMPOSE}")
        return 1
    try:
        proc = subprocess.run(
            ["docker", "compose", "-f", str(COMPOSE), "config"],
            capture_output=True,
            text=True,
            timeout=60,
        )
    except FileNotFoundError:
        print("Docker nao instalado — pulando validate (SKIP).")
        return 0
    except subprocess.TimeoutExpired:
        print("docker compose config timeout")
        return 1

    if proc.returncode != 0:
        print(proc.stderr or proc.stdout or "docker compose config falhou")
        return 1

    print("docker-compose.stack.yml OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
