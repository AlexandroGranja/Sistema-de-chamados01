import json
from datetime import date, datetime, timedelta, timezone
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import String, cast, func, or_, text
from sqlalchemy.orm import Session

from app.api.v1.dependencies import get_current_user
from app.core.config import settings
from app.core.database import get_db
from app.models.ticket import Ticket, TicketImpact, TicketPriority, TicketStatus, TicketType, TicketUrgency
from app.models.ticket_history import TicketHistory
from app.models.user import User, UserRole
from app.schemas.ticket import (
    DeviceCondition,
    OffboardingAction,
    StaffRequesterAlertItem,
    StaffRequesterAlertsOut,
    TicketCreate,
    TicketOffboardingCreate,
    TicketOut,
    TicketStatusUpdate,
    TicketUpdate,
)
from app.services.telefones import sync_offboarding_to_telefones
from app.services.telefones import get_offboarding_prefill

router = APIRouter()


def _forbid_portal_requester(user: User) -> None:
    """Usuários só do portal não acessam fluxos de desligamento / edição avançada."""
    if user.role == UserRole.REQUESTER:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Acesso negado para usuários do cadastro público.",
        )


def _normalize_status_raw(status_raw) -> str:
    if status_raw is None:
        return ""
    if hasattr(status_raw, "value"):
        return str(status_raw.value).strip().lower()
    return str(status_raw).strip().lower()


def _requester_can_edit_ticket_status(status_raw) -> bool:
    """Portal: só edita enquanto não estiver resolvido, encerrado ou cancelado."""
    s = _normalize_status_raw(status_raw)
    return s not in ("resolved", "closed", "cancelled")


def _is_postgres_db() -> bool:
    url = str(settings.DATABASE_URL or "")
    return url.startswith("postgresql") or "postgres" in url.lower()


def _effective_user_app_id(current_user: User) -> int:
    """
    No SSO unificado, o id do usuário do `usuarios_app` é salvo em `users.snipe_user_id`.
    """
    if current_user.snipe_user_id is not None:
        return int(current_user.snipe_user_id)
    # fallback: alguns usuários legados podem não ter snipe_user_id populado
    return int(current_user.id)


def _map_ticket_type(db_tipo: str) -> TicketType:
    s = str(db_tipo or "").strip().lower()
    mapping = {
        "gerenciamento": TicketType.REQUEST,
        "request": TicketType.REQUEST,
        "maintenance": TicketType.MAINTENANCE,
        "incident": TicketType.INCIDENT,
        "problem": TicketType.PROBLEM,
    }
    return mapping.get(s, TicketType.REQUEST)


def _map_priority(db_prio: str) -> TicketPriority:
    s = str(db_prio or "").strip().lower()
    mapping = {
        "normal": TicketPriority.MEDIUM,
        "medium": TicketPriority.MEDIUM,
        "media": TicketPriority.MEDIUM,
        "high": TicketPriority.HIGH,
        "alta": TicketPriority.HIGH,
        "critical": TicketPriority.CRITICAL,
        "critial": TicketPriority.CRITICAL,
        "critico": TicketPriority.CRITICAL,
        "crítico": TicketPriority.CRITICAL,
        "low": TicketPriority.LOW,
        "baixo": TicketPriority.LOW,
    }
    return mapping.get(s, TicketPriority.MEDIUM)


def _map_status(db_status: str) -> TicketStatus:
    s = str(db_status or "").strip().lower()
    s_norm = s.replace(" ", "_").replace("-", "_")
    mapping = {
        "aberto": TicketStatus.OPEN,
        "in_analysis": TicketStatus.IN_ANALYSIS,
        "in_analise": TicketStatus.IN_ANALYSIS,
        "em_analise": TicketStatus.IN_ANALYSIS,
        "em_análise": TicketStatus.IN_ANALYSIS,
        "in_progress": TicketStatus.IN_PROGRESS,
        "em_andamento": TicketStatus.IN_PROGRESS,
        "waiting_user": TicketStatus.WAITING_USER,
        "aguardando_usuario": TicketStatus.WAITING_USER,
        "aguardando usuário": TicketStatus.WAITING_USER,
        "waiting_third_party": TicketStatus.WAITING_THIRD_PARTY,
        "waiting_thirdparty": TicketStatus.WAITING_THIRD_PARTY,
        "resolved": TicketStatus.RESOLVED,
        "fechado": TicketStatus.CLOSED,
        "encerrado": TicketStatus.CLOSED,
        "closed": TicketStatus.CLOSED,
        "cancelled": TicketStatus.CANCELLED,
        "cancelado": TicketStatus.CANCELLED,
    }
    return mapping.get(s_norm, mapping.get(s, TicketStatus.OPEN))


def _ticket_out_from_row(row: dict) -> dict:
    status_enum = _map_status(row.get("status"))
    priority_enum = _map_priority(row.get("prioridade"))
    type_enum = _map_ticket_type(row.get("tipo"))
    fechou_em = row.get("fechado_em")

    resolved_at = fechou_em if status_enum == TicketStatus.RESOLVED else None
    closed_at = fechou_em if status_enum == TicketStatus.CLOSED else None

    return {
        "id": int(row["id"]),
        "ticket_number": str(row.get("numero_chamado") or row["id"]),
        "title": row.get("titulo") or "",
        "description": row.get("descricao") or "",
        "ticket_type": type_enum,
        "category": row.get("category"),
        "subcategory": row.get("subcategory"),
        "priority": priority_enum,
        "urgency": None,
        "impact": None,
        "status": status_enum,
        "requester_id": int(row.get("solicitante_id") or 0),
        "assigned_technician_id": row.get("responsavel_id"),
        "location": row.get("location"),
        "equipment_info": row.get("equipment_info"),
        "internal_notes": row.get("internal_notes"),
        "created_at": row.get("aberto_em"),
        "updated_at": row.get("atualizado_em"),
        "resolved_at": resolved_at,
        "closed_at": closed_at,
        "requester_name": None,
        "requester_role": None,
    }


def _attach_requester_user(db: Session, ticket_dict: dict, solicitante_id: Optional[int]) -> None:
    """
    Preenche requester_name / requester_role.
    `solicitante_id` em `chamados` pode ser `users.id` ou o id em `usuarios_app` (guardado em users.snipe_user_id).
    """
    ticket_dict["requester_name"] = None
    ticket_dict["requester_role"] = None
    if solicitante_id is None:
        return
    try:
        sid = int(solicitante_id)
    except (TypeError, ValueError):
        return
    if sid <= 0:
        return
    u = (
        db.query(User)
        .filter(or_(User.id == sid, User.snipe_user_id == sid))
        .first()
    )
    if not u:
        return
    ticket_dict["requester_name"] = u.name
    ticket_dict["requester_role"] = u.role.value if hasattr(u.role, "value") else str(u.role)


def _finalize_ticket_pg_out(db: Session, row) -> dict:
    """Monta o dict de saída PostgreSQL + nome do solicitante."""
    r = dict(row)
    d = _ticket_out_from_row(r)
    _attach_requester_user(db, d, r.get("solicitante_id"))
    return d


def _next_business_day(base: date) -> date:
    next_day = base + timedelta(days=1)
    while next_day.weekday() >= 5:
        next_day += timedelta(days=1)
    return next_day


def _create_history(db: Session, ticket_id: int, user_id: int, action: str, old: Optional[str], new: Optional[str]):
    db.add(
        TicketHistory(
            ticket_id=ticket_id,
            user_id=user_id,
            action_type=action,
            old_value=old,
            new_value=new,
        )
    )


def _serialize_offboarding_metadata(payload: TicketOffboardingCreate, status_name: str) -> str:
    reference_date = payload.return_date or datetime.now().date()
    due_date = _next_business_day(reference_date)
    data = {
        "employee_name": payload.employee_name,
        "asset_tag": payload.asset_tag,
        "device_model": payload.device_model,
        "user_department": payload.user_department,
        "return_date": reference_date.isoformat(),
        "next_business_day": due_date.isoformat(),
        "device_condition": payload.device_condition.value,
        "maintenance_reason": payload.maintenance_reason,
        "resolution_text": payload.resolution_text,
        "action": payload.action.value,
        "suggested_status": status_name,
    }
    return json.dumps(data, ensure_ascii=False)


def _offboarding_template(payload: TicketOffboardingCreate):
    action = payload.action
    employee = payload.employee_name
    asset = payload.asset_tag or "não informado"
    device_model = payload.device_model or "não informado"
    user_department = payload.user_department or "não informado"
    return_date_date = payload.return_date or datetime.now().date()
    return_date = return_date_date.isoformat()
    return_date_br = return_date_date.strftime("%d/%m/%Y")

    if action == OffboardingAction.DEVICE_OK:
        title = f"Desligamento - aparelho OK - {employee}"
        description = (
            f"Colaborador: {employee}\n"
            f"Equipe: {user_department}\n"
            f"Data de devolução: {return_date}\n"
            f"Ativo: {asset}\n"
            f"Modelo: {device_model}\n"
            "Ação: aparelho recebido e validado em condições de uso."
        )
        return title, description, TicketStatus.CLOSED, TicketType.REQUEST, "Recebimento de Aparelho"

    if action == OffboardingAction.OFFBOARDING_WITH_MAINTENANCE:
        reason = payload.maintenance_reason or "motivo não informado"
        title = f"Desligamento com manutenção - {employee}"
        description = (
            f"Colaborador: {employee}\n"
            f"Equipe: {user_department}\n"
            f"Data de devolução: {return_date}\n"
            f"Ativo: {asset}\n"
            f"Modelo: {device_model}\n"
            f"Ação: desligamento com aparelho para manutenção.\n"
            f"Motivo: {reason}"
        )
        return title, description, TicketStatus.WAITING_USER, TicketType.MAINTENANCE, "Manutenção"

    if action == OffboardingAction.MAINTENANCE_ONLY:
        reason = payload.maintenance_reason or "motivo não informado"
        title = f"Manutenção de aparelho - {employee}"
        description = (
            f"Colaborador: {employee}\n"
            f"Equipe: {user_department}\n"
            f"Data de devolução: {return_date}\n"
            f"Ativo: {asset}\n"
            f"Modelo: {device_model}\n"
            "Ação: manutenção de aparelho sem desligamento.\n"
            f"Motivo: {reason}"
        )
        return title, description, TicketStatus.WAITING_THIRD_PARTY, TicketType.MAINTENANCE, "Manutenção"

    if action == OffboardingAction.WITHOUT_CHARGER:
        due = _next_business_day(payload.return_date or datetime.now().date()).strftime("%d/%m/%Y")
        title = f"Desligamento sem carregador - {employee}"
        description = (
            f"Colaborador: {employee}\n"
            f"Equipe: {user_department}\n"
            f"Data de devolução: {return_date}\n"
            f"Ativo: {asset}\n"
            f"Modelo: {device_model}\n"
            f"Ação: o aparelho foi testado e se encontra em condições de uso, porém o carregador não foi entregue. "
            f"O usuário {employee} foi avisado que tem 1 dia útil para realizar a entrega do carregador "
            f"(prazo: {due}).\n"
            f"Condição do aparelho: {payload.device_condition.value}."
        )
        if payload.device_condition == DeviceCondition.MAINTENANCE and payload.maintenance_reason:
            description += f"\nMotivo manutenção: {payload.maintenance_reason}"
        return title, description, TicketStatus.WAITING_USER, TicketType.REQUEST, "Recebimento de Aparelho"

    due = _next_business_day(payload.return_date or datetime.now().date()).strftime("%d/%m/%Y")
    title = f"Desligamento sem entrega - {employee}"
    description = (
        f"Colaborador: {employee}\n"
        f"Equipe: {user_department}\n"
        f"Data de referência: {return_date_br}\n"
        f"Modelo: {device_model}\n"
        "Ação: usuário não entregou aparelho e o carregador.\n"
        f"Prazo para entrega: {due}."
    )
    return title, description, TicketStatus.WAITING_USER, TicketType.REQUEST, "Recebimento de Aparelho"


@router.get("", response_model=List[TicketOut])
async def list_tickets(
    status_filter: Optional[TicketStatus] = None,
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if _is_postgres_db():
        user_app_id = _effective_user_app_id(current_user)

        where_sql = "WHERE 1=1"
        params: dict[str, object] = {"skip": int(skip), "limit": int(limit)}

        if current_user.role not in [UserRole.ADMIN, UserRole.TECHNICIAN]:
            where_sql += " AND c.solicitante_id = :user_id"
            params["user_id"] = user_app_id

        if status_filter:
            where_sql += " AND c.status = :status_filter"
            params["status_filter"] = status_filter.value

        sql = text(
            f"""
            SELECT
                c.id,
                c.numero_chamado,
                c.tipo,
                c.status,
                c.prioridade,
                c.titulo,
                c.descricao,
                c.category,
                c.subcategory,
                c.location,
                c.equipment_info,
                c.internal_notes,
                c.solicitante_id,
                c.responsavel_id,
                c.aberto_em,
                c.atualizado_em,
                c.fechado_em
            FROM chamados c
            {where_sql}
            ORDER BY c.id DESC
            OFFSET :skip
            LIMIT :limit
            """
        )

        rows = db.execute(sql, params).mappings().all()
        out = []
        for r in rows:
            d = _ticket_out_from_row(dict(r))
            _attach_requester_user(db, d, r.get("solicitante_id"))
            out.append(d)
        return out

    # fallback (SQLite/legado)
    query = db.query(Ticket)
    if current_user.role not in [UserRole.ADMIN, UserRole.TECHNICIAN]:
        query = query.filter(Ticket.requester_id == current_user.id)
    if status_filter:
        query = query.filter(Ticket.status == status_filter)
    rows = query.order_by(Ticket.id.desc()).offset(skip).limit(limit).all()
    out_sqlite = []
    for t in rows:
        td = TicketOut.model_validate(t).model_dump()
        _attach_requester_user(db, td, t.requester_id)
        out_sqlite.append(TicketOut(**td))
    return out_sqlite


def _status_is_terminal_raw(status_raw) -> bool:
    """Status final: alerta some quando o chamado passa para um destes."""
    if status_raw is None:
        return False
    if hasattr(status_raw, "value") and not isinstance(status_raw, str):
        raw_str = str(status_raw.value)
    else:
        raw_str = str(status_raw)
    try:
        st = _map_status(raw_str)
    except Exception:
        st = TicketStatus.OPEN
    return st in (TicketStatus.RESOLVED, TicketStatus.CLOSED, TicketStatus.CANCELLED)


@router.get("/staff-requester-alerts", response_model=StaffRequesterAlertsOut)
async def staff_requester_alerts(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Para admin/técnico: lista chamados do portal (solicitante `requester`) que ainda **não** foram
    encerrados (resolved/closed/cancelled). O painel mantém o aviso visível até o chamado ser atualizado
    para status final; o som toca quando entra um ID novo na lista.
    """
    if current_user.role not in (UserRole.ADMIN, UserRole.TECHNICIAN):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Apenas administradores ou técnicos podem consultar alertas de chamados.",
        )

    now = datetime.now(timezone.utc)
    items: List[StaffRequesterAlertItem] = []

    if _is_postgres_db():
        sql = text(
            """
            SELECT DISTINCT ON (c.id)
                c.id,
                c.numero_chamado,
                c.titulo,
                c.aberto_em,
                c.status AS status_raw,
                u.name AS requester_name
            FROM chamados c
            INNER JOIN users u
                ON (u.id = c.solicitante_id OR u.snipe_user_id = c.solicitante_id)
            WHERE lower(cast(u.role AS VARCHAR)) = :requester_role
            ORDER BY c.id, c.aberto_em DESC
            """
        )
        rows = db.execute(sql, {"requester_role": UserRole.REQUESTER.value}).mappings().all()
        for r in rows:
            if _status_is_terminal_raw(r.get("status_raw")):
                continue
            items.append(
                StaffRequesterAlertItem(
                    id=int(r["id"]),
                    ticket_number=str(r.get("numero_chamado") or r["id"]),
                    title=str(r.get("titulo") or ""),
                    created_at=r["aberto_em"],
                    requester_name=r.get("requester_name"),
                )
            )
        items.sort(key=lambda x: x.created_at or datetime.min.replace(tzinfo=timezone.utc), reverse=True)
    else:
        rows = (
            db.query(Ticket, User.name)
            .join(User, Ticket.requester_id == User.id)
            .filter(func.lower(cast(User.role, String)) == UserRole.REQUESTER.value)
            .order_by(Ticket.created_at.desc())
            .all()
        )
        for t, req_name in rows:
            if _status_is_terminal_raw(t.status):
                continue
            td = TicketOut.model_validate(t).model_dump()
            items.append(
                StaffRequesterAlertItem(
                    id=int(td["id"]),
                    ticket_number=str(td.get("ticket_number") or td["id"]),
                    title=str(td.get("title") or ""),
                    created_at=td["created_at"],
                    requester_name=req_name,
                )
            )

    return StaffRequesterAlertsOut(items=items, server_time=now)


@router.post("", response_model=TicketOut, status_code=status.HTTP_201_CREATED)
async def create_ticket(
    payload: TicketCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if _is_postgres_db():
        user_app_id = _effective_user_app_id(current_user)
        requester_id = payload.requester_id or user_app_id
        if requester_id != user_app_id and current_user.role not in [UserRole.ADMIN, UserRole.TECHNICIAN]:
            raise HTTPException(
                status_code=403,
                detail="Acesso negado para criar chamado em nome de outro usuário.",
            )

        status_val = payload.status.value
        should_close = payload.status in [TicketStatus.RESOLVED, TicketStatus.CLOSED]
        priority_val = payload.priority.value

        responsavel_id = payload.assigned_technician_id
        if current_user.role not in [UserRole.ADMIN, UserRole.TECHNICIAN]:
            responsavel_id = None

        sql = text(
            """
            WITH next_num AS (
                SELECT COALESCE(MAX(id), 0) + 1 AS nid FROM chamados
            )
            INSERT INTO chamados (
                numero_chamado, tipo, status, prioridade, origem,
                titulo, descricao,
                solicitante_id, responsavel_id,
                category, subcategory, location,
                equipment_info, internal_notes,
                fechado_em
            )
            SELECT
                nid::text,
                :tipo,
                :status,
                :prioridade,
                'gerenciamento',
                :titulo,
                :descricao,
                :solicitante_id,
                :responsavel_id,
                :category,
                :subcategory,
                :location,
                NULL,
                NULL,
                CASE WHEN :should_close THEN NOW() ELSE NULL END
            FROM next_num
            RETURNING
                id, numero_chamado, tipo, status, prioridade, titulo, descricao,
                category, subcategory, location,
                equipment_info, internal_notes,
                solicitante_id, responsavel_id,
                aberto_em, atualizado_em, fechado_em
            """
        )

        row = db.execute(
            sql,
            {
                "tipo": payload.ticket_type.value,
                "status": status_val,
                "prioridade": priority_val,
                "titulo": payload.title.strip(),
                "descricao": payload.description.strip(),
                "solicitante_id": int(requester_id),
                "responsavel_id": int(responsavel_id) if responsavel_id is not None else None,
                "category": payload.category.strip() if payload.category else None,
                "subcategory": payload.subcategory.strip() if payload.subcategory else None,
                "location": payload.location.strip() if payload.location else None,
                "should_close": bool(should_close),
            },
        ).mappings().first()

        if not row:
            raise HTTPException(status_code=500, detail="Falha ao criar chamado.")

        db.commit()
        return _finalize_ticket_pg_out(db, row)

    requester_id = payload.requester_id or current_user.id
    if requester_id != current_user.id and current_user.role not in [UserRole.ADMIN, UserRole.TECHNICIAN]:
        raise HTTPException(status_code=403, detail="Acesso negado para criar chamado em nome de outro usuário.")

    ticket = Ticket(
        ticket_number="TMP",
        title=payload.title,
        description=payload.description,
        ticket_type=payload.ticket_type,
        category=payload.category,
        subcategory=payload.subcategory,
        priority=payload.priority,
        urgency=payload.urgency,
        impact=payload.impact,
        status=payload.status,
        requester_id=requester_id,
        assigned_technician_id=payload.assigned_technician_id,
        location=payload.location,
        equipment_info=payload.equipment_info,
        internal_notes=payload.internal_notes,
    )
    db.add(ticket)
    db.flush()
    ticket.ticket_number = str(ticket.id)
    _create_history(db, ticket.id, current_user.id, "created", None, f"Ticket {ticket.id}")
    db.commit()
    db.refresh(ticket)
    return ticket


@router.post("/offboarding", response_model=TicketOut, status_code=status.HTTP_201_CREATED)
async def create_offboarding_ticket(
    payload: TicketOffboardingCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _forbid_portal_requester(current_user)
    if _is_postgres_db():
        user_app_id = _effective_user_app_id(current_user)
        title, description, target_status, ticket_type, item = _offboarding_template(payload)
        equipment_info = _serialize_offboarding_metadata(payload, target_status.value)
        metadata = json.loads(equipment_info)
        now = datetime.now(timezone.utc)

        responsavel_id = user_app_id if current_user.role in [UserRole.ADMIN, UserRole.TECHNICIAN] else None

        sql = text(
            """
            WITH next_num AS (
                SELECT COALESCE(MAX(id), 0) + 1 AS nid FROM chamados
            )
            INSERT INTO chamados (
                numero_chamado, tipo, status, prioridade, origem,
                titulo, descricao,
                solicitante_id, responsavel_id,
                category, subcategory, location,
                equipment_info, internal_notes,
                fechado_em
            )
            SELECT
                nid::text,
                :tipo,
                :status,
                :prioridade,
                'gerenciamento',
                :titulo,
                :descricao,
                :solicitante_id,
                :responsavel_id,
                :category,
                :subcategory,
                :location,
                :equipment_info,
                :internal_notes,
                CASE WHEN :should_close THEN NOW() ELSE NULL END
            FROM next_num
            RETURNING
                id, numero_chamado, tipo, status, prioridade, titulo, descricao,
                category, subcategory, location,
                equipment_info, internal_notes,
                solicitante_id, responsavel_id,
                aberto_em, atualizado_em, fechado_em
            """
        )

        row = db.execute(
            sql,
            {
                "tipo": ticket_type.value,
                "status": target_status.value,
                "prioridade": TicketPriority.MEDIUM.value,
                "titulo": title,
                "descricao": description,
                "solicitante_id": int(user_app_id),
                "responsavel_id": int(responsavel_id) if responsavel_id is not None else None,
                "category": (payload.user_department or "Sem setor").strip() if payload.user_department else "Sem setor",
                "subcategory": item,
                "location": None,
                "equipment_info": equipment_info,
                "internal_notes": payload.resolution_text or payload.maintenance_reason,
                "should_close": bool(target_status in [TicketStatus.RESOLVED, TicketStatus.CLOSED]),
            },
        ).mappings().first()

        if not row:
            raise HTTPException(status_code=500, detail="Falha ao criar chamado de desligamento.")

        ticket_id = int(row["id"])
        # Regra do seu fluxo:
        # - `not_delivered`: não mexe no Gerenciamento na abertura; mexe quando fechar o chamado.
        if payload.action == OffboardingAction.NOT_DELIVERED:
            sync_ok = True
            sync_message = "Telefones: sincronizacao pendente (not_delivered) ate o chamado ser fechado."
        else:
            sync_ok, sync_message = sync_offboarding_to_telefones(
                enabled=settings.TELEFONES_SYNC_ENABLED,
                db_path=settings.TELEFONES_DB_PATH,
                employee_name=payload.employee_name,
                asset_tag=payload.asset_tag or "",
                action=payload.action.value,
                maintenance_reason=payload.maintenance_reason or "",
                return_date=(payload.return_date.isoformat() if payload.return_date else ""),
                ticket_id=ticket_id,
            )

        metadata["telefones_sync_ok"] = sync_ok
        metadata["telefones_sync_message"] = sync_message

        db.execute(
            text(
                """
                UPDATE chamados
                SET equipment_info = :equipment_info,
                    atualizado_em = NOW()
                WHERE id = :id
                """
            ),
            {"equipment_info": json.dumps(metadata, ensure_ascii=False), "id": ticket_id},
        )
        db.commit()

        # recarrega para garantir consistencia
        row = db.execute(
            text("SELECT * FROM chamados WHERE id = :id"),
            {"id": ticket_id},
        ).mappings().first()

        return _finalize_ticket_pg_out(db, row)

    title, description, target_status, ticket_type, item = _offboarding_template(payload)
    equipment_info = _serialize_offboarding_metadata(payload, target_status.value)
    metadata = json.loads(equipment_info)
    now = datetime.now(timezone.utc)

    ticket = Ticket(
        ticket_number="TMP",
        title=title,
        description=description,
        ticket_type=ticket_type,
        category=payload.user_department or "Sem setor",
        subcategory=item,
        priority=TicketPriority.MEDIUM,
        urgency=TicketUrgency.MEDIUM,
        impact=TicketImpact.MEDIUM,
        status=target_status,
        requester_id=current_user.id,
        assigned_technician_id=current_user.id if current_user.role in [UserRole.ADMIN, UserRole.TECHNICIAN] else None,
        equipment_info=equipment_info,
        internal_notes=payload.resolution_text or payload.maintenance_reason,
        resolved_at=now if target_status in [TicketStatus.RESOLVED, TicketStatus.CLOSED] else None,
        closed_at=now if target_status == TicketStatus.CLOSED else None,
    )
    db.add(ticket)
    db.flush()
    ticket.ticket_number = str(ticket.id)
    _create_history(db, ticket.id, current_user.id, "created_offboarding", None, payload.action.value)
    if payload.action == OffboardingAction.NOT_DELIVERED:
        _create_history(db, ticket.id, current_user.id, "pending_delivery", None, "Aguardando usuário")

    sync_ok, sync_message = sync_offboarding_to_telefones(
        enabled=settings.TELEFONES_SYNC_ENABLED,
        db_path=settings.TELEFONES_DB_PATH,
        employee_name=payload.employee_name,
        asset_tag=payload.asset_tag or "",
        action=payload.action.value,
        maintenance_reason=payload.maintenance_reason or "",
        return_date=(payload.return_date.isoformat() if payload.return_date else ""),
        ticket_id=ticket.id,
    )
    metadata["telefones_sync_ok"] = sync_ok
    metadata["telefones_sync_message"] = sync_message
    ticket.equipment_info = json.dumps(metadata, ensure_ascii=False)
    if sync_ok:
        _create_history(db, ticket.id, current_user.id, "telefones_sync", None, sync_message)
    else:
        _create_history(db, ticket.id, current_user.id, "telefones_sync_error", None, sync_message)

    db.commit()
    db.refresh(ticket)
    return ticket


@router.get("/offboarding-prefill")
async def offboarding_prefill(
    employee_name: str,
    current_user: User = Depends(get_current_user),
):
    _forbid_portal_requester(current_user)
    ok, message, data = get_offboarding_prefill(
        db_path=settings.TELEFONES_DB_PATH,
        employee_name=employee_name,
    )
    return {
        "ok": ok,
        "message": message,
        "data": data,
    }


@router.put("/{ticket_id}/status", response_model=TicketOut)
async def update_ticket_status(
    ticket_id: int,
    payload: TicketStatusUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _forbid_portal_requester(current_user)
    if _is_postgres_db():
        user_app_id = _effective_user_app_id(current_user)

        row = db.execute(
            text(
                """
                SELECT
                    id, numero_chamado, tipo, status, prioridade, titulo, descricao,
                    category, subcategory, location,
                    equipment_info, internal_notes,
                    solicitante_id, responsavel_id,
                    aberto_em, atualizado_em, fechado_em
                FROM chamados
                WHERE id = :id
                """
            ),
            {"id": int(ticket_id)},
        ).mappings().first()

        if not row:
            raise HTTPException(status_code=404, detail="Chamado não encontrado.")

        if current_user.role not in [UserRole.ADMIN, UserRole.TECHNICIAN] and int(row.get("solicitante_id") or 0) != user_app_id:
            raise HTTPException(status_code=403, detail="Acesso negado.")

        previous_status = row.get("status")
        new_status = payload.status.value

        internal_notes = row.get("internal_notes")
        if payload.internal_notes:
            merged_notes = [internal_notes, payload.internal_notes]
            internal_notes = "\n\n".join(x for x in merged_notes if x)

        should_set_close = payload.status in [TicketStatus.RESOLVED, TicketStatus.CLOSED]
        db.execute(
            text(
                """
                UPDATE chamados
                SET status = :status,
                    atualizado_em = NOW(),
                    fechado_em = CASE
                        WHEN :should_close THEN COALESCE(fechado_em, NOW())
                        ELSE fechado_em
                    END,
                    internal_notes = :internal_notes
                WHERE id = :id
                """
            ),
            {
                "status": new_status,
                "should_close": bool(should_set_close),
                "internal_notes": internal_notes,
                "id": int(ticket_id),
            },
        )
        db.commit()

        row = db.execute(
            text(
                """
                SELECT
                    id, numero_chamado, tipo, status, prioridade, titulo, descricao,
                    category, subcategory, location,
                    equipment_info, internal_notes,
                    solicitante_id, responsavel_id,
                    aberto_em, atualizado_em, fechado_em
                FROM chamados
                WHERE id = :id
                """
            ),
            {"id": int(ticket_id)},
        ).mappings().first()
        # Regra do seu fluxo:
        # - Ao fechar `not_delivered`, sincroniza a linha para ficar VAGO.
        try:
            new_status_norm = (payload.status.value if hasattr(payload.status, "value") else str(payload.status)).lower()
            if new_status_norm in ["closed", "resolved"] and row:
                eq_info = row.get("equipment_info")
                if eq_info:
                    metadata = json.loads(eq_info) if isinstance(eq_info, str) else {}
                    if metadata.get("action") == OffboardingAction.NOT_DELIVERED.value:
                        sync_offboarding_to_telefones(
                            enabled=settings.TELEFONES_SYNC_ENABLED,
                            db_path=settings.TELEFONES_DB_PATH,
                            employee_name=metadata.get("employee_name") or "",
                            asset_tag=metadata.get("asset_tag") or "",
                            action=OffboardingAction.NOT_DELIVERED.value,
                            maintenance_reason=metadata.get("maintenance_reason") or "",
                            return_date=metadata.get("return_date") or "",
                            ticket_id=int(row.get("id") or ticket_id),
                        )
        except Exception:
            # Não quebrar fechamento do ticket por falha na sincronização.
            pass

        return _finalize_ticket_pg_out(db, row)

    ticket = db.query(Ticket).filter(Ticket.id == ticket_id).first()
    if not ticket:
        raise HTTPException(status_code=404, detail="Chamado não encontrado.")

    if current_user.role not in [UserRole.ADMIN, UserRole.TECHNICIAN] and ticket.requester_id != current_user.id:
        raise HTTPException(status_code=403, detail="Acesso negado.")

    previous = ticket.status.value
    ticket.status = payload.status
    if payload.internal_notes:
        merged_notes = [ticket.internal_notes, payload.internal_notes]
        ticket.internal_notes = "\n\n".join(x for x in merged_notes if x)
    now = datetime.now(timezone.utc)
    if payload.status in [TicketStatus.RESOLVED, TicketStatus.CLOSED] and not ticket.resolved_at:
        ticket.resolved_at = now
    if payload.status == TicketStatus.CLOSED:
        ticket.closed_at = now

    _create_history(db, ticket.id, current_user.id, "status_changed", previous, payload.status.value)
    db.commit()
    db.refresh(ticket)
    return ticket


@router.put("/{ticket_id}", response_model=TicketOut)
async def update_ticket(
    ticket_id: int,
    payload: TicketUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    is_requester = current_user.role == UserRole.REQUESTER
    if _is_postgres_db():
        user_app_id = _effective_user_app_id(current_user)

        row = db.execute(
            text(
                """
                SELECT
                    id, numero_chamado, tipo, status, prioridade, titulo, descricao,
                    category, subcategory, location,
                    equipment_info, internal_notes,
                    solicitante_id, responsavel_id,
                    aberto_em, atualizado_em, fechado_em
                FROM chamados
                WHERE id = :id
                """
            ),
            {"id": int(ticket_id)},
        ).mappings().first()

        if not row:
            raise HTTPException(status_code=404, detail="Chamado não encontrado.")

        if current_user.role not in [UserRole.ADMIN, UserRole.TECHNICIAN] and int(row.get("solicitante_id") or 0) != user_app_id:
            raise HTTPException(status_code=403, detail="Acesso negado.")

        if is_requester:
            if not _requester_can_edit_ticket_status(row.get("status")):
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Este chamado não pode mais ser editado (resolvido, encerrado ou cancelado).",
                )
            if payload.status is not None:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Você não pode alterar o status do chamado pelo portal.",
                )
            if payload.internal_notes is not None:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Observações internas não podem ser alteradas pelo portal.",
                )

        updated_fields: dict[str, object] = {}

        if payload.title is not None:
            cleaned_title = payload.title.strip()
            if not cleaned_title:
                raise HTTPException(status_code=400, detail="Título não pode ficar vazio.")
            updated_fields["titulo"] = cleaned_title

        if payload.description is not None:
            cleaned_description = payload.description.strip()
            if not cleaned_description:
                raise HTTPException(status_code=400, detail="Descrição não pode ficar vazia.")
            updated_fields["descricao"] = cleaned_description

        if payload.category is not None:
            updated_fields["category"] = payload.category.strip() or None

        if payload.subcategory is not None:
            updated_fields["subcategory"] = payload.subcategory.strip() or None

        if payload.location is not None:
            updated_fields["location"] = payload.location.strip() or None

        # metadata em `equipment_info`
        equipment_info = row.get("equipment_info")
        metadata = {}
        if equipment_info:
            try:
                metadata = json.loads(equipment_info)
                if not isinstance(metadata, dict):
                    metadata = {}
            except Exception:
                metadata = {}

        metadata_updated = False

        if not is_requester and payload.user_department is not None:
            cleaned_team = payload.user_department.strip() or None
            metadata["user_department"] = cleaned_team
            updated_fields["category"] = cleaned_team
            metadata_updated = True

        if not is_requester and payload.device_model is not None:
            metadata["device_model"] = payload.device_model.strip() or None
            metadata_updated = True

        if not is_requester and payload.asset_tag is not None:
            metadata["asset_tag"] = payload.asset_tag.strip() or None
            metadata_updated = True

        if not is_requester and payload.reason is not None:
            cleaned_reason = payload.reason.strip() or None
            metadata["maintenance_reason"] = cleaned_reason
            metadata["resolution_text"] = cleaned_reason
            metadata_updated = True

        if metadata_updated:
            updated_fields["equipment_info"] = json.dumps(metadata, ensure_ascii=False)

        # status/resolução (equipe; não pelo portal)
        previous_status = row.get("status")
        if not is_requester and payload.status is not None:
            status_val = payload.status.value
            updated_fields["status"] = status_val
            if payload.status in [TicketStatus.RESOLVED, TicketStatus.CLOSED]:
                # só seta se ainda não tem fechado_em
                if row.get("fechado_em") is None:
                    updated_fields["fechado_em"] = datetime.now(timezone.utc)

        # internal_notes substitui (como no legado)
        if not is_requester and payload.internal_notes is not None:
            updated_fields["internal_notes"] = payload.internal_notes.strip() or None

        # sempre atualiza timestamp
        updated_fields["atualizado_em"] = datetime.now(timezone.utc)

        # monta UPDATE dinamico
        set_fragments = ", ".join([f"{k} = :{k}" for k in updated_fields.keys()])
        params = {k: v for k, v in updated_fields.items()}
        params["id"] = int(ticket_id)

        db.execute(
            text(
                f"""
                UPDATE chamados
                SET {set_fragments}
                WHERE id = :id
                """
            ),
            params,
        )
        db.commit()

        row = db.execute(
            text(
                """
                SELECT
                    id, numero_chamado, tipo, status, prioridade, titulo, descricao,
                    category, subcategory, location,
                    equipment_info, internal_notes,
                    solicitante_id, responsavel_id,
                    aberto_em, atualizado_em, fechado_em
                FROM chamados
                WHERE id = :id
                """
            ),
            {"id": int(ticket_id)},
        ).mappings().first()

        return _finalize_ticket_pg_out(db, row)

    ticket = db.query(Ticket).filter(Ticket.id == ticket_id).first()
    if not ticket:
        raise HTTPException(status_code=404, detail="Chamado não encontrado.")

    if current_user.role not in [UserRole.ADMIN, UserRole.TECHNICIAN] and ticket.requester_id != current_user.id:
        raise HTTPException(status_code=403, detail="Acesso negado.")

    if is_requester:
        if not _requester_can_edit_ticket_status(ticket.status):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Este chamado não pode mais ser editado (resolvido, encerrado ou cancelado).",
            )
        if payload.status is not None:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Você não pode alterar o status do chamado pelo portal.",
            )
        if payload.internal_notes is not None:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Observações internas não podem ser alteradas pelo portal.",
            )

    if payload.title is not None:
        cleaned_title = payload.title.strip()
        if not cleaned_title:
            raise HTTPException(status_code=400, detail="Título não pode ficar vazio.")
        ticket.title = cleaned_title

    if payload.description is not None:
        cleaned_description = payload.description.strip()
        if not cleaned_description:
            raise HTTPException(status_code=400, detail="Descrição não pode ficar vazia.")
        ticket.description = cleaned_description

    if payload.category is not None:
        ticket.category = payload.category.strip() or None
    if payload.subcategory is not None:
        ticket.subcategory = payload.subcategory.strip() or None
    if payload.location is not None:
        ticket.location = payload.location.strip() or None

    metadata = {}
    if ticket.equipment_info:
        try:
            metadata = json.loads(ticket.equipment_info)
            if not isinstance(metadata, dict):
                metadata = {}
        except Exception:
            metadata = {}

    metadata_updated = False

    if not is_requester and payload.user_department is not None:
        cleaned_team = payload.user_department.strip() or None
        metadata["user_department"] = cleaned_team
        ticket.category = cleaned_team
        metadata_updated = True

    if not is_requester and payload.device_model is not None:
        metadata["device_model"] = payload.device_model.strip() or None
        metadata_updated = True

    if not is_requester and payload.asset_tag is not None:
        metadata["asset_tag"] = payload.asset_tag.strip() or None
        metadata_updated = True

    if not is_requester and payload.reason is not None:
        cleaned_reason = payload.reason.strip() or None
        metadata["maintenance_reason"] = cleaned_reason
        metadata["resolution_text"] = cleaned_reason
        metadata_updated = True

    if metadata_updated:
        ticket.equipment_info = json.dumps(metadata, ensure_ascii=False)

    previous_status = ticket.status.value
    if not is_requester and payload.status is not None:
        ticket.status = payload.status
        now = datetime.now(timezone.utc)
        if payload.status in [TicketStatus.RESOLVED, TicketStatus.CLOSED] and not ticket.resolved_at:
            ticket.resolved_at = now
        if payload.status == TicketStatus.CLOSED:
            ticket.closed_at = now

    if not is_requester and payload.internal_notes is not None:
        # Na edição completa do chamado, a observação deve substituir o conteúdo atual.
        ticket.internal_notes = payload.internal_notes.strip() or None

    if not is_requester and payload.status is not None and previous_status != ticket.status.value:
        _create_history(db, ticket.id, current_user.id, "status_changed", previous_status, ticket.status.value)
    _create_history(db, ticket.id, current_user.id, "updated", None, "Campos do chamado atualizados")

    db.commit()
    db.refresh(ticket)
    return ticket
