"""
Módulo de Desligamento de Usuário: dar baixa em ativos no Gerenciamento de Ativos (Snipe-IT)
e informar condição (perfeitas condições ou precisa manutenção).
"""
import os
import logging
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from typing import List

from app.core.database import get_db
from app.models.user import User
from app.models.offboarding_log import OffboardingLog
from app.models.asset_assignment import AssetAssignment
from app.schemas.desligamento import (
    CheckinRequest,
    CheckoutRequest,
    CheckoutByTagRequest,
    OffboardingLogSchema,
    AssetAssignmentSchema,
)
from app.api.v1.dependencies import get_current_user, get_current_technician_or_admin
from app.services.snipe import (
    is_configured,
    list_users as snipe_list_users,
    find_user_by_name_or_email,
    get_assets_assigned_to_user,
    get_available_assets,
    get_status_labels,
    checkin_asset_by_condition,
    checkout_asset as snipe_checkout_asset,
    delete_user as snipe_delete_user,
    ensure_user_by_full_name,
    find_available_asset_by_tag,
    diagnose_api as diagnose_snipe_api,
)

router = APIRouter()
logger = logging.getLogger(__name__)

# Valor fixo no carregamento do módulo (mesmo que startup) para evitar divergência em runtime
_SNIPE_CONFIGURED_AT_LOAD = bool(
    is_configured()
    or (os.environ.get("SNIPE_BASE_URL") and os.environ.get("SNIPE_API_TOKEN"))
)


def _snipe_configured_for_frontend() -> bool:
    """True se a integração foi considerada configurada na subida ou no .env."""
    try:
        from app.core.snipe_status import snipe_configured_at_startup
        if snipe_configured_at_startup:
            return True
    except Exception:
        pass
    if _SNIPE_CONFIGURED_AT_LOAD:
        return True
    try:
        from app.core.config import settings, _env_path, _env_encoding
        if getattr(settings, "SNIPE_BASE_URL", "") and getattr(settings, "SNIPE_API_TOKEN", ""):
            return True
        if _env_path.exists():
            with open(_env_path, "r", encoding=_env_encoding, errors="ignore") as f:
                content = f.read().lstrip("\ufeff")
            has_base = any(
                line.strip().startswith("SNIPE_BASE_URL=") and line.split("=", 1)[1].strip()
                for line in content.splitlines()
            )
            for line in content.splitlines():
                line = line.strip()
                if line.startswith("SNIPE_API_TOKEN="):
                    token = line.split("=", 1)[1].strip().strip("'\"").strip()
                    if has_base and len(token) > 10:
                        return True
                    break
    except Exception as e:
        logger.debug("snipe_configured_for_frontend: %s", e)
    return False


@router.get("/snipe-status")
async def get_snipe_status():
    """Verifica se a integração com o Gerenciamento de Ativos está configurada. Público para o frontend."""
    configured = _snipe_configured_for_frontend()
    # Fallback: ler backend/.env por path absoluto (evita divergência de cwd/encoding)
    if not configured:
        try:
            from pathlib import Path
            env_file = Path(__file__).resolve().parent.parent.parent.parent.parent / ".env"
            if env_file.exists():
                with open(env_file, "r", encoding="utf-8", errors="ignore") as f:
                    raw = f.read().lstrip("\ufeff")
                if "SNIPE_BASE_URL=" in raw and "SNIPE_API_TOKEN=" in raw:
                    for line in raw.splitlines():
                        if line.strip().startswith("SNIPE_API_TOKEN="):
                            tok = (line.split("=", 1)[1] or "").strip().strip("'\"")
                            if len(tok) > 10:
                                configured = True
                            break
        except Exception:
            pass
    return JSONResponse(
        content={"configured": configured},
        headers={"Cache-Control": "no-store, no-cache, must-revalidate", "Pragma": "no-cache"},
    )


@router.get("/statuslabels")
async def list_status_labels(
    current_user: User = Depends(get_current_technician_or_admin),
):
    """Lista os status disponíveis no Gerenciamento de Ativos (ex.: Ready to Deploy, Manutenção)."""
    if not is_configured():
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Integração com Gerenciamento de Ativos não configurada.",
        )
    labels = get_status_labels()
    return {"data": labels}


@router.get("/snipe-diagnostico")
async def snipe_diagnostico(
    current_user: User = Depends(get_current_technician_or_admin),
):
    """
    Diagnóstico rápido da conectividade com a API do Gerenciamento de Ativos.
    """
    return diagnose_snipe_api()


@router.get("/usuarios-snipe")
async def list_snipe_users(
    search: str = "",
    current_user: User = Depends(get_current_technician_or_admin),
):
    """Lista usuários (pessoas) do Gerenciamento de Ativos para vincular ao desligamento."""
    try:
        if not is_configured():
            return {"data": []}
        users = snipe_list_users(search=search or None)
        return {"data": users or []}
    except Exception as e:
        logger.warning("usuarios-snipe: %s", e)
        return {"data": []}


@router.get("/ativos/{snipe_user_id}")
async def list_assets_for_user(
    snipe_user_id: int,
    current_user: User = Depends(get_current_technician_or_admin),
):
    """Lista ativos atribuídos a um usuário no Gerenciamento de Ativos (para dar baixa)."""
    if not is_configured():
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Integração com Gerenciamento de Ativos não configurada.",
        )
    assets = get_assets_assigned_to_user(snipe_user_id)
    return {"data": assets}


@router.get("/buscar-usuario-snipe")
async def find_snipe_user(
    name: str = "",
    email: str = "",
    current_user: User = Depends(get_current_technician_or_admin),
):
    """
    Busca um usuário no Gerenciamento de Ativos por nome ou email.
    Útil para descobrir o ID Snipe a partir do usuário do sistema de chamados.
    """
    if not is_configured():
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Integração com Gerenciamento de Ativos não configurada.",
        )
    user = find_user_by_name_or_email(name=name or None, email=email or None)
    if not user:
        return {"data": None}
    return {"data": user}


@router.post("/checkin", status_code=status.HTTP_200_OK)
async def checkin_asset(
    body: CheckinRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_technician_or_admin),
):
    """
    Dá baixa em um ativo no Gerenciamento de Ativos (check-in).
    Define o status conforme a condição: perfeitas condições (Ready to Deploy) ou Manutenção.
    """
    if not is_configured():
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Integração com Gerenciamento de Ativos não configurada.",
        )
    try:
        result = checkin_asset_by_condition(
            asset_id=body.asset_id,
            needs_maintenance=body.needs_maintenance,
            note=body.note,
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Erro ao dar baixa no Gerenciamento de Ativos: {str(e)}",
        )
    # Salvar log local (Snipe pode retornar payload ou objeto direto)
    payload = result.get("payload") if isinstance(result, dict) else result
    if not isinstance(payload, dict):
        payload = {}
    asset_tag = payload.get("asset_tag") or ""
    asset_name = payload.get("name") or ""
    log = OffboardingLog(
        user_id=body.user_id,
        snipe_asset_id=body.asset_id,
        asset_tag=asset_tag or None,
        asset_name=asset_name or None,
        needs_maintenance=body.needs_maintenance,
        note=body.note,
        created_by_id=current_user.id,
    )
    db.add(log)
    db.commit()
    db.refresh(log)
    deleted_snipe_user = False
    remaining_assets = None
    if body.delete_user_when_no_assets and body.snipe_user_id:
        try:
            remaining = get_assets_assigned_to_user(body.snipe_user_id)
            remaining_assets = len(remaining or [])
            if remaining_assets == 0:
                snipe_delete_user(body.snipe_user_id)
                deleted_snipe_user = True
        except Exception as e:
            # Não bloqueia a baixa do ativo se a exclusão do usuário falhar.
            logger.warning("Não foi possível excluir usuário Snipe %s após check-in: %s", body.snipe_user_id, e)

    return {
        "message": "Baixa realizada com sucesso no Gerenciamento de Ativos.",
        "log_id": log.id,
        "snipe_response": result,
        "deleted_snipe_user": deleted_snipe_user,
        "remaining_assets_for_user": remaining_assets,
    }


@router.get("/logs", response_model=List[OffboardingLogSchema])
async def list_offboarding_logs(
    skip: int = 0,
    limit: int = 50,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_technician_or_admin),
):
    """Lista o histórico de baixas (check-in) realizadas no desligamento."""
    logs = (
        db.query(OffboardingLog)
        .order_by(OffboardingLog.created_at.desc())
        .offset(skip)
        .limit(limit)
        .all()
    )
    return logs


# ---- Entrega de ativo (check-out) ----

@router.get("/ativos-disponiveis")
async def list_available_assets(
    current_user: User = Depends(get_current_technician_or_admin),
):
    """Lista ativos disponíveis no Gerenciamento de Ativos (para entrega a usuários)."""
    try:
        if not is_configured():
            return {"data": []}
        assets = get_available_assets()
        return {"data": assets or []}
    except Exception as e:
        logger.warning("ativos-disponiveis: %s", e)
        return {"data": []}


@router.post("/checkout", status_code=status.HTTP_200_OK)
async def checkout_asset(
    body: CheckoutRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_technician_or_admin),
):
    """
    Entrega um ativo a um usuário (check-out no Gerenciamento de Ativos).
    Atualiza o Snipe-IT e grava no sistema quem recebeu o aparelho.
    """
    if not is_configured():
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Integração com Gerenciamento de Ativos não configurada.",
        )
    try:
        result = snipe_checkout_asset(
            asset_id=body.asset_id,
            snipe_user_id=body.snipe_user_id,
            note=body.note,
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Erro ao entregar ativo no Gerenciamento de Ativos: {str(e)}",
        )
    payload = result.get("payload") if isinstance(result, dict) else result
    if not isinstance(payload, dict):
        payload = {}
    asset_tag = payload.get("asset_tag") or ""
    asset_name = payload.get("name") or ""
    assigned_to = payload.get("assigned_to") or {}
    snipe_user_name = assigned_to.get("name") if isinstance(assigned_to, dict) else None
    assignment = AssetAssignment(
        user_id=body.user_id,
        snipe_user_id=body.snipe_user_id,
        snipe_user_name=snipe_user_name,
        snipe_asset_id=body.asset_id,
        asset_tag=asset_tag or None,
        asset_name=asset_name or None,
        note=body.note,
        assigned_by_id=current_user.id,
    )
    db.add(assignment)
    db.commit()
    db.refresh(assignment)
    return {
        "message": "Ativo entregue com sucesso. Atualizado no Gerenciamento de Ativos.",
        "assignment_id": assignment.id,
        "snipe_response": result,
    }


@router.post("/checkout-por-patrimonio", status_code=status.HTTP_200_OK)
async def checkout_asset_by_tag(
    body: CheckoutByTagRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_technician_or_admin),
):
    """
    Entrega um ativo informando colaborador (nome completo) e patrimônio.
    Se o colaborador não existir no Snipe-IT, ele é criado automaticamente.
    """
    if not is_configured():
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Integração com Gerenciamento de Ativos não configurada.",
        )

    collaborator_name = (body.collaborator_name or "").strip()
    asset_tag = (body.asset_tag or "").strip()
    if not collaborator_name:
        raise HTTPException(status_code=400, detail="Nome completo do colaborador é obrigatório.")
    if not asset_tag:
        raise HTTPException(status_code=400, detail="Patrimônio do ativo é obrigatório.")

    try:
        snipe_user = ensure_user_by_full_name(collaborator_name)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Erro ao localizar/criar colaborador no Gerenciamento de Ativos: {str(e)}",
        )

    asset = find_available_asset_by_tag(asset_tag)
    if not asset or not asset.get("id"):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Ativo '{asset_tag}' não encontrado ou não está disponível para entrega.",
        )

    try:
        result = snipe_checkout_asset(
            asset_id=asset["id"],
            snipe_user_id=snipe_user["id"],
            note=body.note,
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Erro ao entregar ativo no Gerenciamento de Ativos: {str(e)}",
        )

    payload = result.get("payload") if isinstance(result, dict) else result
    if not isinstance(payload, dict):
        payload = {}

    assignment = AssetAssignment(
        user_id=body.user_id,
        snipe_user_id=snipe_user["id"],
        snipe_user_name=snipe_user.get("name") or collaborator_name,
        snipe_asset_id=asset["id"],
        asset_tag=(payload.get("asset_tag") or asset.get("asset_tag") or asset_tag) or None,
        asset_name=(payload.get("name") or asset.get("name") or "") or None,
        note=body.note,
        assigned_by_id=current_user.id,
    )
    db.add(assignment)
    db.commit()
    db.refresh(assignment)

    return {
        "message": "Ativo entregue com sucesso por patrimônio.",
        "assignment_id": assignment.id,
        "snipe_user": {"id": snipe_user.get("id"), "name": snipe_user.get("name") or collaborator_name},
        "asset": {"id": asset.get("id"), "asset_tag": asset.get("asset_tag"), "serial": asset.get("serial")},
        "snipe_response": result,
    }


@router.get("/atribuicoes", response_model=List[AssetAssignmentSchema])
async def list_assignments(
    skip: int = 0,
    limit: int = 50,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_technician_or_admin),
):
    """Lista o histórico de entregas de ativos (quem recebeu qual aparelho)."""
    rows = (
        db.query(AssetAssignment)
        .order_by(AssetAssignment.assigned_at.desc())
        .offset(skip)
        .limit(limit)
        .all()
    )
    return rows
