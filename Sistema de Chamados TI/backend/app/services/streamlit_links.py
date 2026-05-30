"""Deep links do React (Chamados) para o Gerenciamento de Telefones (Streamlit)."""

from __future__ import annotations

from urllib.parse import urlencode

from app.core.config import settings


def build_streamlit_linha_url(
    *,
    ticket_id: int | None = None,
    linha: str = "",
    segmento: str = "",
    equipe: str = "",
    return_url: str = "",
) -> str:
    """Monta URL do Streamlit com contexto de chamado e retorno ao React."""
    base = (settings.STREAMLIT_APP_URL or "http://localhost:8501").rstrip("/")
    params: dict[str, str] = {}

    if ticket_id is not None and int(ticket_id) > 0:
        params["ticket_id"] = str(int(ticket_id))

    linha_val = (linha or "").strip()
    if linha_val:
        params["linha"] = linha_val

    segmento_val = (segmento or "").strip()
    if segmento_val:
        params["segmento_chamado"] = segmento_val

    equipe_val = (equipe or "").strip()
    if equipe_val:
        params["equipe_chamado"] = equipe_val

    retorno = (return_url or "").strip()
    if not retorno and ticket_id is not None and int(ticket_id) > 0:
        frontend = (settings.FRONTEND_URL or "http://localhost:3000").rstrip("/")
        retorno = f"{frontend}/tickets?ticket_id={int(ticket_id)}"
    if retorno:
        params["return_url"] = retorno

    if not params:
        return f"{base}/"
    return f"{base}/?{urlencode(params)}"
