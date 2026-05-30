"""Teste C1: GET /api/telefones/linhas com login unificado."""

from __future__ import annotations

import os
import sys

import requests
from dotenv import load_dotenv

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
load_dotenv(os.path.join(ROOT, ".env"))

API = os.environ.get("CHAMADOS_API_URL", "http://127.0.0.1:8000").rstrip("/")
USER = os.environ.get("E2E_LOGIN_USER", "alexandro granja")
PASS = sys.argv[1].strip() if len(sys.argv) > 1 else os.environ.get("E2E_LOGIN_PASS", "")


def main() -> int:
    if not PASS:
        print("Uso: python -m scripts.test_c1_linhas_api <senha>")
        return 1

    login = requests.post(
        f"{API}/api/auth/login",
        json={"email": USER, "password": PASS},
        timeout=20,
    )
    if login.status_code != 200:
        print(f"Login falhou ({login.status_code}): {login.text[:200]}")
        return 1
    token = login.json().get("access_token")
    headers = {"Authorization": f"Bearer {token}"}

    ativas_data = None
    for modo in ("ativas", "desativadas"):
        r = requests.get(
            f"{API}/api/telefones/linhas",
            params={"modo": modo},
            headers=headers,
            timeout=60,
        )
        if r.status_code != 200:
            print(f"GET /linhas?modo={modo} FAIL ({r.status_code}): {r.text[:300]}")
            return 1
        data = r.json()
        if modo == "ativas":
            ativas_data = data
        total = data.get("total", 0)
        sample = (data.get("rows") or [{}])[0]
        keys = [k.encode("ascii", "replace").decode("ascii") for k in list(sample.keys())[:5]]
        print(f"modo={modo} total={total} sample_keys={keys}")

    if ativas_data and ativas_data.get("rows"):
        one = ativas_data["rows"][0]
        wr = requests.post(
            f"{API}/api/telefones/linhas/salvar-lote",
            json={"modo": "ativas", "rows": [one]},
            headers=headers,
            timeout=60,
        )
        if wr.status_code != 200:
            print(f"POST salvar-lote FAIL ({wr.status_code}): {wr.text[:300]}")
            return 1
        print(f"salvar-lote total={wr.json().get('total')}")

    print("C1 linhas API PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
