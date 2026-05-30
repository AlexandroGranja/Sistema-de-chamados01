"""Cliente HTTP Streamlit → API /api/telefones (Fase C1)."""

from __future__ import annotations

import logging
from typing import Optional

import pandas as pd
import requests

from src.core.config import get_chamados_api_url, use_telefones_api

logger = logging.getLogger(__name__)

_api_token: Optional[str] = None


def is_enabled() -> bool:
    return use_telefones_api()


def set_api_token(token: Optional[str]) -> None:
    global _api_token
    _api_token = (token or "").strip() or None


def get_api_token() -> Optional[str]:
    return _api_token


def login_chamados_api(username: str, password: str, *, timeout: float = 20.0) -> Optional[str]:
    """Obtém JWT da API usando as mesmas credenciais do Streamlit."""
    base = get_chamados_api_url()
    if not base:
        return None
    try:
        resp = requests.post(
            f"{base}/api/auth/login",
            json={"email": username.strip(), "password": password},
            timeout=timeout,
        )
        if resp.status_code != 200:
            logger.warning("Login API Chamados falhou (%s): %s", resp.status_code, resp.text[:200])
            return None
        token = (resp.json() or {}).get("access_token")
        return str(token).strip() if token else None
    except Exception as exc:
        logger.warning("Login API Chamados erro: %s", exc)
        return None


def _headers() -> dict[str, str]:
    token = get_api_token()
    if not token:
        raise RuntimeError("Token da API Chamados não configurado.")
    return {"Authorization": f"Bearer {token}"}


def load_linhas_via_api(modo: str = "ativas", *, timeout: float = 60.0) -> pd.DataFrame:
    """Carrega grid de linhas via GET /api/telefones/linhas."""
    base = get_chamados_api_url()
    resp = requests.get(
        f"{base}/api/telefones/linhas",
        params={"modo": modo},
        headers=_headers(),
        timeout=timeout,
    )
    if resp.status_code != 200:
        raise RuntimeError(f"API linhas HTTP {resp.status_code}: {resp.text[:300]}")
    payload = resp.json() or {}
    rows = payload.get("rows") or []
    if not rows:
        return pd.DataFrame()
    return pd.DataFrame(rows)


def save_linhas_via_api(df: pd.DataFrame, modo: str = "ativas", *, timeout: float = 120.0) -> int:
    """Persiste grid via POST /api/telefones/linhas/salvar-lote."""
    base = get_chamados_api_url()
    rows = df.where(pd.notna(df), None).to_dict(orient="records")
    resp = requests.post(
        f"{base}/api/telefones/linhas/salvar-lote",
        json={"modo": modo, "rows": rows},
        headers=_headers(),
        timeout=timeout,
    )
    if resp.status_code != 200:
        raise RuntimeError(f"API salvar-lote HTTP {resp.status_code}: {resp.text[:300]}")
    payload = resp.json() or {}
    return int(payload.get("total") or 0)
