"""Testes unitarios C3 — regras de acesso Streamlit admin-only."""

from __future__ import annotations

import os

from src.core.streamlit_access import (
    has_operational_chamado_context,
    is_streamlit_admin_only,
    resolve_streamlit_access,
)


def _run() -> int:
    assert is_streamlit_admin_only() is True

    os.environ["STREAMLIT_ADMIN_ONLY"] = "false"
    assert is_streamlit_admin_only() is False
    os.environ["STREAMLIT_ADMIN_ONLY"] = "true"

    assert has_operational_chamado_context(chamado_id="42") is True
    assert has_operational_chamado_context(linha="2199", return_url="http://x/tickets/1") is True
    assert has_operational_chamado_context(linha="2199") is False
    assert has_operational_chamado_context() is False

    assert resolve_streamlit_access(is_admin=True, page="painel") == "admin_full"
    assert resolve_streamlit_access(is_admin=False, page="config") == "blocked_config"
    assert (
        resolve_streamlit_access(
            is_admin=False,
            page="painel",
            chamado_id="7",
            linha="21993158681",
        )
        == "operador_chamado"
    )
    assert resolve_streamlit_access(is_admin=False, page="painel") == "blocked_panel"

    assert (
        resolve_streamlit_access(
            is_admin=False,
            page="painel",
            admin_only=False,
        )
        == "admin_full"
    )

    print("C3 streamlit_access PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(_run())
