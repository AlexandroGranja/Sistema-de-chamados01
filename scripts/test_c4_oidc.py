"""Teste C4: endpoints OIDC (modo desligado por padrao)."""

from __future__ import annotations

import os
import sys

import requests
from dotenv import load_dotenv

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
load_dotenv(os.path.join(ROOT, ".env"))

API = os.environ.get("CHAMADOS_API_URL", "http://127.0.0.1:8000").rstrip("/")


def main() -> int:
    try:
        r = requests.get(f"{API}/api/auth/oidc/status", timeout=10)
    except Exception as exc:
        print(f"API indisponivel ({API}): {exc}")
        return 1

    if r.status_code != 200:
        print(f"oidc/status HTTP {r.status_code}: {r.text[:200]}")
        return 1

    data = r.json()
    enabled = bool(data.get("enabled"))
    print(f"oidc/status enabled={enabled} issuer={data.get('issuer') or '-'}")

    if enabled:
        print("OIDC ativo — configure Keycloak conforme doc/C4_OIDC_KEYCLOAK.md")
    else:
        print("OIDC desligado (padrao) — SSO por codigo continua disponivel")

    r2 = requests.get(f"{API}/api/auth/oidc/login", timeout=10, allow_redirects=False)
    if enabled:
        assert r2.status_code in (302, 307), r2.status_code
    else:
        assert r2.status_code == 404, r2.status_code

    print("C4 OIDC PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
