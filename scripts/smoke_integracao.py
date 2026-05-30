"""Smoke test de integração: serviços no ar + banco acessível.

Uso:
    python -m scripts.smoke_integracao
    python -m scripts.smoke_integracao --api-url http://127.0.0.1:8000
"""

from __future__ import annotations

import argparse
import os
import sys

import requests

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

DEFAULT_API = os.environ.get("CHAMADOS_API_URL", "http://127.0.0.1:8000").rstrip("/")
DEFAULT_STREAMLIT = os.environ.get("STREAMLIT_APP_URL", "http://127.0.0.1:8501").rstrip("/")
DEFAULT_WEB = os.environ.get("CHAMADOS_WEB_URL", "http://127.0.0.1:3000").rstrip("/")


def _check_http(name: str, url: str, timeout: float = 8.0) -> tuple[bool, str]:
    try:
        resp = requests.get(url, timeout=timeout)
        if resp.status_code < 500:
            return True, f"{name}: OK ({resp.status_code}) — {url}"
        return False, f"{name}: HTTP {resp.status_code} — {url}"
    except Exception as exc:
        return False, f"{name}: FAIL — {url} ({exc})"


def _check_database() -> tuple[bool, str]:
    try:
        from src.core.config import is_postgres_configured
        from src.db.repository import get_connection
    except ImportError as exc:
        return False, f"Banco: FAIL — import ({exc})"

    if not is_postgres_configured():
        return False, "Banco: FAIL — DATABASE_URL não configurado (.env)"

    conn = None
    try:
        conn = get_connection()
        with conn.cursor() as cur:
            cur.execute("SELECT COUNT(*) FROM linhas WHERE modo = 'ativas'")
            ativas = int(cur.fetchone()[0])
            cur.execute("SELECT COUNT(*) FROM auditoria")
            auditoria = int(cur.fetchone()[0])
        return True, f"Banco: OK — linhas ativas={ativas}, auditoria={auditoria}"
    except Exception as exc:
        return False, f"Banco: FAIL — {exc}"
    finally:
        if conn is not None:
            try:
                conn.close()
            except Exception:
                pass


def main() -> int:
    parser = argparse.ArgumentParser(description="Smoke test integração Gerenciamento + Chamados")
    parser.add_argument("--api-url", default=DEFAULT_API)
    parser.add_argument("--web-url", default=DEFAULT_WEB)
    parser.add_argument("--streamlit-url", default=DEFAULT_STREAMLIT)
    args = parser.parse_args()

    checks: list[tuple[bool, str]] = []

    checks.append(_check_http("API Chamados", f"{args.api_url.rstrip('/')}/"))
    checks.append(_check_http("API docs", f"{args.api_url.rstrip('/')}/docs"))
    checks.append(_check_http("Chamados web", f"{args.web_url.rstrip('/')}/"))
    checks.append(_check_http("Gerenciamento", f"{args.streamlit_url.rstrip('/')}/"))
    checks.append(_check_database())

    print("Smoke integração — Gerenciamento + Chamados\n")
    failed = 0
    for ok, msg in checks:
        print(("PASS" if ok else "FAIL") + " | " + msg)
        if not ok:
            failed += 1

    if failed:
        print(f"\n{failed} check(s) falharam. Verifique ativador_completo.bat e doc/SETUP_BANCO_LOCAL.md")
        return 1

    print("\nSmoke PASS — ambiente pronto para QA manual (doc/CHECKLIST_QA_INTEGRACAO.md)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
