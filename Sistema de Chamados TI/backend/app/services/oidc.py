"""OIDC (Keycloak) — Fase C4. Opcional; SSO por codigo permanece como fallback."""

from __future__ import annotations

import secrets
import time
from typing import Any
from urllib.parse import urlencode

import requests

from app.core.config import settings

_pending_states: dict[str, float] = {}
_pending_exchanges: dict[str, dict[str, Any]] = {}
_STATE_TTL_SEC = 600
_EXCHANGE_TTL_SEC = 120


def oidc_enabled() -> bool:
    return bool(settings.OIDC_ENABLED and settings.OIDC_ISSUER and settings.OIDC_CLIENT_ID)


def _cleanup() -> None:
    now = time.time()
    for store in (_pending_states, _pending_exchanges):
        dead = [k for k, exp in store.items() if exp < now]
        for k in dead:
            store.pop(k, None)


def public_config() -> dict[str, Any]:
    return {
        "enabled": oidc_enabled(),
        "issuer": settings.OIDC_ISSUER if oidc_enabled() else "",
        "login_path": "/api/auth/oidc/login" if oidc_enabled() else "",
    }


def _discovery() -> dict[str, Any]:
    issuer = settings.OIDC_ISSUER.rstrip("/")
    url = f"{issuer}/.well-known/openid-configuration"
    resp = requests.get(url, timeout=15)
    resp.raise_for_status()
    return resp.json()


def build_login_redirect(state: str | None = None) -> tuple[str, str]:
    if not oidc_enabled():
        raise RuntimeError("OIDC desabilitado")
    _cleanup()
    state = state or secrets.token_urlsafe(24)
    _pending_states[state] = time.time() + _STATE_TTL_SEC
    meta = _discovery()
    params = {
        "client_id": settings.OIDC_CLIENT_ID,
        "response_type": "code",
        "scope": settings.OIDC_SCOPES,
        "redirect_uri": settings.OIDC_REDIRECT_URI,
        "state": state,
    }
    url = f"{meta['authorization_endpoint']}?{urlencode(params)}"
    return url, state


def verify_state(state: str) -> bool:
    _cleanup()
    exp = _pending_states.pop(str(state or "").strip(), None)
    return exp is not None and exp >= time.time()


def exchange_authorization_code(code: str) -> dict[str, Any]:
    if not oidc_enabled():
        raise RuntimeError("OIDC desabilitado")
    meta = _discovery()
    data = {
        "grant_type": "authorization_code",
        "code": code,
        "redirect_uri": settings.OIDC_REDIRECT_URI,
        "client_id": settings.OIDC_CLIENT_ID,
    }
    if settings.OIDC_CLIENT_SECRET:
        data["client_secret"] = settings.OIDC_CLIENT_SECRET
    resp = requests.post(meta["token_endpoint"], data=data, timeout=20)
    resp.raise_for_status()
    return resp.json()


def fetch_userinfo(access_token: str) -> dict[str, Any]:
    meta = _discovery()
    resp = requests.get(
        meta["userinfo_endpoint"],
        headers={"Authorization": f"Bearer {access_token}"},
        timeout=15,
    )
    resp.raise_for_status()
    return resp.json()


def store_jwt_exchange(access_token: str, refresh_token: str) -> str:
    _cleanup()
    code = secrets.token_urlsafe(32)
    _pending_exchanges[code] = {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "exp": time.time() + _EXCHANGE_TTL_SEC,
    }
    return code


def pop_jwt_exchange(code: str) -> dict[str, str] | None:
    _cleanup()
    raw = _pending_exchanges.pop(str(code or "").strip(), None)
    if not raw or raw.get("exp", 0) < time.time():
        return None
    return {
        "access_token": str(raw["access_token"]),
        "refresh_token": str(raw["refresh_token"]),
    }


def logout_url(id_token_hint: str = "") -> str:
    if not oidc_enabled():
        return ""
    try:
        meta = _discovery()
        end_session = meta.get("end_session_endpoint")
        if not end_session:
            return ""
        params = {"post_logout_redirect_uri": settings.FRONTEND_URL.rstrip("/")}
        if id_token_hint:
            params["id_token_hint"] = id_token_hint
        return f"{end_session}?{urlencode(params)}"
    except Exception:
        return ""
