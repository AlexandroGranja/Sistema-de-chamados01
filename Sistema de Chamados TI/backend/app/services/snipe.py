"""
Integração com o sistema de Gerenciamento de Ativos (Snipe-IT).
Base URL típica: http://192.168.200.131:8082
"""
import logging
from typing import Any, Optional
from datetime import datetime

import requests
from app.core.config import settings

logger = logging.getLogger(__name__)

HEADERS = {
    "Accept": "application/json",
    "Content-Type": "application/json",
}


def _url(path: str) -> str:
    base = settings.SNIPE_BASE_URL.rstrip("/")
    return f"{base}/api/v1{path}"


def _auth_headers() -> dict:
    h = dict(HEADERS)
    if settings.SNIPE_API_TOKEN:
        h["Authorization"] = f"Bearer {settings.SNIPE_API_TOKEN}"
    return h


def _get(path: str, params: Optional[dict] = None) -> dict:
    """GET na API Snipe-IT. Retorna o JSON ou levanta em caso de erro."""
    resp = requests.get(
        _url(path),
        headers=_auth_headers(),
        params=params or {},
        timeout=30,
    )
    resp.raise_for_status()
    return resp.json()


def _post(path: str, json: dict) -> dict:
    """POST na API Snipe-IT."""
    resp = requests.post(
        _url(path),
        headers=_auth_headers(),
        json=json,
        timeout=30,
    )
    resp.raise_for_status()
    return resp.json() if resp.content else {}


def _delete(path: str) -> dict:
    """DELETE na API Snipe-IT."""
    resp = requests.delete(
        _url(path),
        headers=_auth_headers(),
        timeout=30,
    )
    resp.raise_for_status()
    return resp.json() if resp.content else {}


def is_configured() -> bool:
    """Retorna True se a integração com Snipe-IT está configurada."""
    # Alguns ambientes podem ter o token vazio (ou não carregado do .env),
    # mas ainda assim o Snipe-IT pode aceitar requisições sem autenticação
    # ou falhar com erro HTTP mais claro. Por isso, consideramos "configurado"
    # quando o BASE_URL existe.
    return bool(settings.SNIPE_BASE_URL)


def list_users(search: Optional[str] = None) -> list[dict]:
    """
    Lista usuários (pessoas) do Snipe-IT.
    search: opcional, busca por nome ou email.
    """
    if not is_configured():
        return []
    try:
        params = {}
        if search:
            params["search"] = search
        data = _get("/users", params=params)
        return data.get("rows", data.get("data", []))
    except requests.exceptions.HTTPError as e:
        body = e.response.text[:500] if e.response is not None and e.response.text else ""
        logger.exception("Erro HTTP ao listar usuários Snipe-IT: %s | body=%s", e, body)
        return []
    except Exception as e:
        logger.exception("Erro ao listar usuários Snipe-IT: %s", e)
        return []


def find_user_by_name_or_email(name: Optional[str] = None, email: Optional[str] = None) -> Optional[dict]:
    """
    Encontra um usuário no Snipe-IT por nome ou email.
    Retorna o primeiro que bater (nome ou email).
    """
    if not name and not email:
        return None
    search = name or email or ""
    users = list_users(search=search)
    name_lower = (name or "").strip().lower()
    email_lower = (email or "").strip().lower()
    for u in users:
        uname = (u.get("name") or "").strip().lower()
        uemail = (u.get("email") or "").strip().lower()
        if name_lower and name_lower in uname:
            return u
        if email_lower and uemail and email_lower in uemail:
            return u
        if search.strip().lower() in uname or (uemail and search.strip().lower() in uemail):
            return u
    return None


def get_assets_assigned_to_user(snipe_user_id: int) -> list[dict]:
    """
    Lista ativos (hardware) atribuídos a um usuário no Snipe-IT.
    """
    if not is_configured():
        return []
    try:
        data = _get("/hardware", params={
            "assigned_to": snipe_user_id,
            "assigned_type": "user",
        })
        return data.get("rows", data.get("data", []))
    except Exception as e:
        logger.exception("Erro ao listar ativos do usuário %s: %s", snipe_user_id, e)
        return []


def get_status_labels() -> list[dict]:
    """Lista os status labels do Snipe-IT (ex.: Ready to Deploy, Manutenção)."""
    if not is_configured():
        return []
    try:
        data = _get("/statuslabels")
        return data.get("rows", data.get("data", []))
    except requests.exceptions.HTTPError as e:
        body = e.response.text[:500] if e.response is not None and e.response.text else ""
        logger.exception("Erro HTTP ao listar status Snipe-IT: %s | body=%s", e, body)
        return []
    except Exception as e:
        logger.exception("Erro ao listar status Snipe-IT: %s", e)
        return []


def checkin_asset(
    asset_id: int,
    status_id: int,
    note: Optional[str] = None,
) -> dict:
    """
    Faz check-in de um ativo no Snipe-IT.
    status_id: ID do status após check-in (ex.: Ready to Deploy = 1, Manutenção = 2).
    """
    if not is_configured():
        raise RuntimeError("Integração com Gerenciamento de Ativos não configurada (SNIPE_BASE_URL e SNIPE_API_TOKEN).")
    body = {"status_id": status_id}
    if note:
        body["note"] = note
    return _post(f"/hardware/{asset_id}/checkin", body)


def checkin_asset_by_condition(
    asset_id: int,
    needs_maintenance: bool,
    note: Optional[str] = None,
) -> dict:
    """
    Faz check-in do ativo definindo o status conforme a condição:
    - needs_maintenance=False -> Ready to Deploy (perfeitas condições)
    - needs_maintenance=True  -> Manutenção
    """
    status_id = settings.SNIPE_STATUS_MAINTENANCE_ID if needs_maintenance else settings.SNIPE_STATUS_READY_ID
    return checkin_asset(asset_id, status_id=status_id, note=note)


def get_available_assets(limit: int = 200) -> list[dict]:
    """
    Lista ativos disponíveis para atribuição (não atribuídos, prontos para implantar).
    """
    if not is_configured():
        return []
    try:
        data = _get("/hardware", params={"limit": limit, "offset": 0})
        rows = data.get("rows", data.get("data", []))
        available = []
        for item in rows:
            assigned = item.get("assigned_to")
            if assigned is None or (isinstance(assigned, dict) and not assigned.get("id")):
                status_label = item.get("status_label") or {}
                stype = (status_label.get("status_type") or "").lower()
                if stype == "deployable" or item.get("status_id") == settings.SNIPE_STATUS_READY_ID:
                    available.append(item)
        return available
    except requests.exceptions.HTTPError as e:
        body = e.response.text[:500] if e.response is not None and e.response.text else ""
        logger.exception("Erro HTTP ao listar ativos disponíveis: %s | body=%s", e, body)
        return []
    except Exception as e:
        logger.exception("Erro ao listar ativos disponíveis: %s", e)
        return []


def checkout_asset(
    asset_id: int,
    snipe_user_id: int,
    note: Optional[str] = None,
) -> dict:
    """
    Atribui um ativo a um usuário no Snipe-IT (check-out / entrega de aparelho).
    """
    if not is_configured():
        raise RuntimeError("Integração com Gerenciamento de Ativos não configurada.")
    # Snipe-IT checkout: assign_to = user id, checkout_to_type = "user"
    body: dict = {
        "checkout_to_type": "user",
        "assigned_user": snipe_user_id,
    }
    if note:
        body["note"] = note
    return _post(f"/hardware/{asset_id}/checkout", body)


def _split_full_name(full_name: str) -> tuple[str, str]:
    parts = [p for p in (full_name or "").strip().split() if p]
    if not parts:
        return "Colaborador", "SemNome"
    if len(parts) == 1:
        return parts[0], "SemSobrenome"
    return parts[0], " ".join(parts[1:])


def ensure_user_by_full_name(full_name: str) -> dict:
    """
    Busca usuário por nome no Snipe-IT e, se não existir, cria um novo colaborador.
    Retorna o objeto do usuário com id.
    """
    if not is_configured():
        raise RuntimeError("Integração com Gerenciamento de Ativos não configurada.")

    name = (full_name or "").strip()
    if not name:
        raise ValueError("Nome do colaborador é obrigatório.")

    # 1) Tenta encontrar já existente
    existing = find_user_by_name_or_email(name=name)
    if existing and existing.get("id"):
        return existing

    # 2) Cria usuário no Snipe-IT
    first_name, last_name = _split_full_name(name)
    timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
    username = f"{first_name.lower().replace(' ', '')}.{last_name.lower().replace(' ', '')}.{timestamp}"
    fake_email = f"{username}@empresa.local"

    payload = {
        "first_name": first_name,
        "last_name": last_name,
        "username": username,
        "email": fake_email,
        "activated": True,
    }
    created = _post("/users", payload)
    if isinstance(created, dict):
        created_payload = created.get("payload") if isinstance(created.get("payload"), dict) else created
        if created_payload.get("id"):
            return created_payload

    # 3) Fallback: busca novamente por nome após tentativa de criação
    existing_after = find_user_by_name_or_email(name=name)
    if existing_after and existing_after.get("id"):
        return existing_after

    raise RuntimeError("Não foi possível encontrar/criar colaborador no Gerenciamento de Ativos.")


def find_available_asset_by_tag(asset_tag: str) -> Optional[dict]:
    """
    Busca ativo disponível por patrimônio/asset_tag (ou serial) no Snipe-IT.
    """
    if not is_configured():
        return None
    target = (asset_tag or "").strip().lower()
    if not target:
        return None

    # Puxa uma lista maior para melhorar chance de achar por patrimônio
    rows = get_available_assets(limit=1000)
    for item in rows:
        tag = str(item.get("asset_tag") or "").strip().lower()
        serial = str(item.get("serial") or "").strip().lower()
        if target in [tag, serial]:
            return item
    return None


def delete_user(user_id: int) -> dict:
    """
    Exclui (soft-delete) usuário no Snipe-IT.
    """
    if not is_configured():
        raise RuntimeError("Integração com Gerenciamento de Ativos não configurada.")
    if not user_id:
        raise ValueError("user_id inválido para exclusão.")
    return _delete(f"/users/{user_id}")


def diagnose_api() -> dict:
    """
    Executa checks básicos da API do Snipe-IT para troubleshooting.
    """
    result = {
        "configured": is_configured(),
        "base_url": settings.SNIPE_BASE_URL,
        "checks": [],
    }
    if not is_configured():
        return result

    headers = _auth_headers()
    tests = [
        ("users", "/users"),
        ("hardware", "/hardware"),
        ("statuslabels", "/statuslabels"),
    ]
    for name, path in tests:
        url = _url(path)
        try:
            resp = requests.get(url, headers=headers, timeout=20)
            snippet = (resp.text or "")[:200]
            result["checks"].append(
                {"endpoint": name, "url": url, "status_code": resp.status_code, "ok": resp.ok, "body_snippet": snippet}
            )
        except Exception as e:
            result["checks"].append(
                {"endpoint": name, "url": url, "status_code": None, "ok": False, "error": str(e)}
            )
    return result
