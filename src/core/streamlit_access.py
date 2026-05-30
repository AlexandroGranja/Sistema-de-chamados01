"""Regras de acesso ao Streamlit — Fase C3 (React operacional + admin-only)."""

from __future__ import annotations

import os
from typing import Literal

StreamlitAccess = Literal[
    "admin_full",
    "operador_chamado",
    "blocked_config",
    "blocked_panel",
]


def is_streamlit_admin_only() -> bool:
    """
    Quando True (padrao C3), operadores usam o React; Streamlit fica admin-only,
    exceto deep link com contexto de chamado/linha (integracao B2).
    """
    raw = os.environ.get("STREAMLIT_ADMIN_ONLY", "true").strip().lower()
    return raw not in {"0", "false", "no", "off"}


def has_operational_chamado_context(
    *,
    chamado_id: str = "",
    linha: str = "",
    return_url: str = "",
) -> bool:
    """Contexto vindo do Chamados (ticket + linha) autoriza edicao limitada no Streamlit."""
    if str(chamado_id or "").strip():
        return True
    if str(linha or "").strip() and str(return_url or "").strip():
        return True
    return False


def resolve_streamlit_access(
    *,
    is_admin: bool,
    page: str,
    chamado_id: str = "",
    linha: str = "",
    return_url: str = "",
    admin_only: bool | None = None,
) -> StreamlitAccess:
    """
    Define o modo de acesso ao Streamlit apos login.

    - admin_full: painel + config (admin ou modo legado dual-UI)
    - operador_chamado: edicao com contexto de ticket (nao-admin)
    - blocked_config: tentativa de abrir config sem ser admin
    - blocked_panel: operador sem deep link do Chamados
    """
    admin_only = is_streamlit_admin_only() if admin_only is None else admin_only
    page = str(page or "painel").strip().lower()

    if page == "config":
        return "admin_full" if is_admin else "blocked_config"

    if not admin_only or is_admin:
        return "admin_full"

    if has_operational_chamado_context(
        chamado_id=chamado_id,
        linha=linha,
        return_url=return_url,
    ):
        return "operador_chamado"

    return "blocked_panel"
