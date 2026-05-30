"""Teste E2E B2: deep links Chamados → Streamlit e geração de return_url."""

from __future__ import annotations

import os
import sys
from urllib.parse import parse_qs, urlparse

import requests
from dotenv import load_dotenv

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BACKEND = os.path.join(ROOT, "Sistema de Chamados TI", "backend")
if ROOT in sys.path:
    sys.path.remove(ROOT)
if BACKEND not in sys.path:
    sys.path.insert(0, BACKEND)
os.chdir(BACKEND)

load_dotenv(os.path.join(ROOT, ".env"))
load_dotenv(os.path.join(BACKEND, ".env"))

API_BASE = os.environ.get("CHAMADOS_API_URL", "http://127.0.0.1:8000").rstrip("/")
LOGIN_USER = os.environ.get("E2E_LOGIN_USER", "alexandro granja")
LOGIN_PASS = os.environ.get("E2E_LOGIN_PASS", "")


def _ensure_api() -> None:
    for path in ("/openapi.json", "/docs"):
        try:
            r = requests.get(f"{API_BASE}{path}", timeout=8)
            if r.status_code in (200, 404):
                return
        except Exception:
            continue
    raise SystemExit(f"API indisponivel em {API_BASE}")


def _login() -> str:
    if not LOGIN_PASS:
        raise SystemExit("Passe a senha: python -m scripts.test_navegacao_b2_e2e <senha>")
    r = requests.post(
        f"{API_BASE}/api/auth/login",
        json={"email": LOGIN_USER, "password": LOGIN_PASS},
        timeout=30,
    )
    if r.status_code != 200:
        raise SystemExit(f"Login falhou ({r.status_code}): {r.text[:300]}")
    token = r.json().get("access_token")
    if not token:
        raise SystemExit("Login sem access_token")
    return token


def _test_build_url_unit() -> None:
    from app.services.streamlit_links import build_streamlit_linha_url

    url = build_streamlit_linha_url(
        ticket_id=42,
        linha="21999990000",
        segmento="Internos",
        equipe="Suporte",
    )
    parsed = urlparse(url)
    qs = parse_qs(parsed.query)
    assert qs.get("ticket_id") == ["42"], f"ticket_id ausente em {url}"
    assert qs.get("linha") == ["21999990000"], f"linha ausente em {url}"
    assert qs.get("segmento_chamado") == ["Internos"], f"segmento ausente em {url}"
    assert qs.get("equipe_chamado") == ["Suporte"], f"equipe ausente em {url}"
    ret = qs.get("return_url", [""])[0]
    assert "ticket_id=42" in ret, f"return_url sem ticket_id: {ret}"
    print(f"  unit build_streamlit_linha_url OK -> {url[:90]}...")


def _test_api_endpoint(token: str) -> str:
    r = requests.get(
        f"{API_BASE}/api/telefones/link-gerenciamento",
        headers={"Authorization": f"Bearer {token}"},
        params={
            "ticket_id": 7,
            "linha": "21993158681",
            "equipe": "Suporte",
        },
        timeout=30,
    )
    if r.status_code != 200:
        raise SystemExit(f"link-gerenciamento falhou ({r.status_code}): {r.text[:400]}")
    url = r.json().get("url") or ""
    if not url.startswith("http"):
        raise SystemExit(f"URL invalida: {url!r}")
    qs = parse_qs(urlparse(url).query)
    if qs.get("ticket_id") != ["7"]:
        raise SystemExit(f"API URL sem ticket_id correto: {url}")
    if qs.get("linha") != ["21993158681"]:
        raise SystemExit(f"API URL sem linha correta: {url}")
    print(f"  GET /link-gerenciamento OK -> {url[:90]}...")
    return url


def main() -> int:
    if len(sys.argv) > 1 and sys.argv[1].strip():
        global LOGIN_PASS
        LOGIN_PASS = sys.argv[1].strip()

    print("B2 — testes automatizados")
    print(f"API: {API_BASE}")

    print("[1/2] Unit: build_streamlit_linha_url")
    _test_build_url_unit()

    print("[2/2] API: GET /api/telefones/link-gerenciamento")
    _ensure_api()
    token = _login()
    _test_api_endpoint(token)

    print("\nE2E B2 PASS (unit + API)")
    print("Pendente manual: clicar botao no React, banner/SSO no Streamlit.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
