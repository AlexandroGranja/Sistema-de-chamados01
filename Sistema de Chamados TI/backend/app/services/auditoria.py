"""Auditoria unificada — grava eventos na tabela `auditoria` (PostgreSQL compartilhado)."""

from __future__ import annotations

import json
import logging
from typing import Any, Optional

from sqlalchemy import text

from app.core.config import settings
from app.core.database import engine

logger = logging.getLogger(__name__)

LINHA_FIELD_LABELS: dict[str, str] = {
    "linha": "Linha",
    "numero_linha": "Linha",
    "nome": "Nome",
    "nome_guerra": "Nome de Guerra",
    "codigo": "Codigo",
    "equipe": "Equipe",
    "equipe_padrao": "EquipePadrao",
    "setor": "Setor",
    "gestor": "Gestor",
    "supervisor": "Supervisor",
    "empresa": "Empresa",
    "cargo": "Cargo",
    "email": "E-mail",
    "imei_a": "IMEI A",
    "imei_b": "IMEI B",
    "marca": "Marca",
    "modelo": "Modelo",
    "aparelho": "Aparelho",
    "numero_serie": "Numero de Serie",
    "ativo": "Ativo",
    "chip": "CHIP",
    "operadora": "Operadora",
    "segmento": "Segmento",
    "observacao": "Observacao",
}

TRACK_FIELDS: list[str] = list(LINHA_FIELD_LABELS.keys())


def _is_postgres_unified() -> bool:
    url = str(settings.DATABASE_URL or "")
    return url.startswith("postgresql") or "postgres" in url.lower()


def _normalize_value(value: Any) -> Any:
    if value is None:
        return None
    text_val = str(value).strip()
    return text_val if text_val else None


def fetch_linha_snapshot(linha_id: int) -> dict[str, Any]:
    """Retorna snapshot completo de uma linha."""
    if not linha_id:
        return {}
    try:
        with engine.connect() as conn:
            row = conn.execute(
                text("SELECT * FROM linhas WHERE id = :id"),
                {"id": linha_id},
            ).mappings().first()
            return dict(row) if row else {}
    except Exception:
        logger.exception("Falha ao ler snapshot da linha id=%s", linha_id)
        return {}


def build_linha_diff(
    antes: dict[str, Any],
    depois: dict[str, Any],
    fields: Optional[list[str]] = None,
) -> list[dict[str, Any]]:
    """Monta lista de alterações campo a campo (formato compatível com o Streamlit)."""
    track = fields or TRACK_FIELDS
    linha_ref = str(
        depois.get("linha")
        or antes.get("linha")
        or depois.get("numero_linha")
        or antes.get("numero_linha")
        or ""
    ).strip()
    alteracoes: list[dict[str, Any]] = []
    for field in track:
        val_antes = _normalize_value(antes.get(field))
        val_depois = _normalize_value(depois.get(field))
        if val_antes == val_depois:
            continue
        alteracoes.append(
            {
                "linha": linha_ref or "—",
                "campo": LINHA_FIELD_LABELS.get(field, field),
                "antes": val_antes if val_antes is not None else "—",
                "depois": val_depois if val_depois is not None else "—",
            }
        )
    return alteracoes


def _enrich_audit_payload(
    antes: Optional[dict[str, Any]],
    depois: Optional[dict[str, Any]],
) -> tuple[dict[str, Any], dict[str, Any]]:
    antes_payload = dict(antes or {})
    depois_payload = dict(depois or {})
    alteracoes = build_linha_diff(antes_payload, depois_payload)
    if not alteracoes:
        return antes_payload, depois_payload

    linhas_editadas = sorted({str(a.get("linha") or "").strip() for a in alteracoes if a.get("linha")})
    campos_alterados = sorted({str(a.get("campo") or "").strip() for a in alteracoes if a.get("campo")})
    meta = {
        "alteracoes": alteracoes,
        "alteracoes_total": len(alteracoes),
        "linhas_editadas": linhas_editadas,
        "campos_alterados": campos_alterados,
    }
    antes_payload.update(meta)
    depois_payload.update(meta)
    return antes_payload, depois_payload


def registrar_auditoria_linha(
    *,
    acao: str,
    linha_id: Optional[int] = None,
    chave_registro: str = "",
    ticket_id: Optional[int] = None,
    antes: Optional[dict[str, Any]] = None,
    depois: Optional[dict[str, Any]] = None,
    detalhes: str = "",
    user_id: Optional[int] = None,
    username: str = "",
    origem: str = "chamados_api",
) -> None:
    """Insere evento na tabela `auditoria`. Falhas são logadas e não quebram o fluxo principal."""
    if not _is_postgres_unified():
        return

    try:
        antes_payload, depois_payload = _enrich_audit_payload(antes, depois)
        chave = (chave_registro or "").strip()
        if not chave and linha_id:
            chave = str(linha_id)
        if not chave and depois_payload:
            chave = str(depois_payload.get("linha") or depois_payload.get("numero_linha") or "")

        chamado_val = int(ticket_id) if ticket_id else None
        user_val = int(user_id) if user_id else None

        with engine.begin() as conn:
            conn.execute(
                text(
                    """
                    INSERT INTO auditoria
                    (acao, entidade, entidade_id, chamado_id, antes_json, depois_json, detalhes, user_id, username, origem)
                    VALUES (:acao, 'linhas', :entidade_id, :chamado_id, :antes_json, :depois_json, :detalhes, :user_id, :username, :origem)
                    """
                ),
                {
                    "acao": acao,
                    "entidade_id": chave,
                    "chamado_id": chamado_val,
                    "antes_json": json.dumps(antes_payload, ensure_ascii=False, default=str)
                    if antes_payload
                    else None,
                    "depois_json": json.dumps(depois_payload, ensure_ascii=False, default=str)
                    if depois_payload
                    else None,
                    "detalhes": (detalhes or "").strip(),
                    "user_id": user_val,
                    "username": (username or "").strip(),
                    "origem": origem,
                },
            )
    except Exception:
        logger.exception("Falha ao registrar auditoria (acao=%s, linha_id=%s)", acao, linha_id)


def audit_linha_update(
    *,
    acao: str,
    linha_id: int,
    antes: dict[str, Any],
    ticket_id: Optional[int] = None,
    detalhes: str = "",
    user_id: Optional[int] = None,
    username: str = "",
) -> None:
    """Audita UPDATE em linha existente (antes + snapshot pós-commit)."""
    depois = fetch_linha_snapshot(linha_id)
    registrar_auditoria_linha(
        acao=acao,
        linha_id=linha_id,
        chave_registro=str(depois.get("linha") or depois.get("numero_linha") or linha_id),
        ticket_id=ticket_id,
        antes=antes,
        depois=depois,
        detalhes=detalhes,
        user_id=user_id,
        username=username,
    )


def audit_linha_create(
    *,
    linha_id: int,
    depois: dict[str, Any],
    ticket_id: Optional[int] = None,
    detalhes: str = "",
    user_id: Optional[int] = None,
    username: str = "",
    acao: str = "criar_linha",
) -> None:
    """Audita INSERT de nova linha."""
    registrar_auditoria_linha(
        acao=acao,
        linha_id=linha_id,
        chave_registro=str(depois.get("linha") or depois.get("numero_linha") or linha_id),
        ticket_id=ticket_id,
        antes={},
        depois=depois,
        detalhes=detalhes,
        user_id=user_id,
        username=username,
    )
