from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from sqlalchemy import String, cast, text, inspect as sa_inspect, func, or_
from typing import List, Optional
from pydantic import EmailStr, TypeAdapter
import re
import secrets
from app.core.database import get_db
from app.core.config import settings
from app.core.security import get_password_hash
from app.core.telefones_auth import hash_password_telefones_style
from app.models.user import User, UserRole
from app.models.ticket import Ticket
from app.models.comment import Comment
from app.models.attachment import Attachment
from app.models.ticket_history import TicketHistory
from app.models.notification import Notification
from app.models.offboarding_log import OffboardingLog
from app.models.asset_assignment import AssetAssignment
from app.schemas.user import UserCreate, UserUpdate, User as UserSchema, UserPasswordUpdate
from app.api.v1.dependencies import get_current_user, get_current_admin
from app.services.snipe import list_users as snipe_list_users, diagnose_api as snipe_diagnose_api

router = APIRouter()


def _is_postgres_unified() -> bool:
    u = str(settings.DATABASE_URL or "")
    return u.startswith("postgresql") or "postgres" in u.lower()


def _has_table(db: Session, name: str) -> bool:
    try:
        return name in sa_inspect(db.get_bind()).get_table_names()
    except Exception:
        return False


def _pick_keeper_usuarios_app_id(db: Session, exclude_id: int) -> int:
    """
    Outro usuário em `usuarios_app` para receber FKs de `chamados` ao excluir permanentemente alguém.
    O PostgreSQL exige que não restem linhas em `chamados` apontando para o id removido.
    """
    row = db.execute(
        text(
            """
            SELECT id FROM usuarios_app
            WHERE ativo = TRUE AND id != :ex
            ORDER BY is_admin DESC, id ASC
            LIMIT 1
            """
        ),
        {"ex": int(exclude_id)},
    ).fetchone()
    if not row:
        row = db.execute(
            text(
                """
                SELECT id FROM usuarios_app
                WHERE id != :ex
                ORDER BY id ASC
                LIMIT 1
                """
            ),
            {"ex": int(exclude_id)},
        ).fetchone()
    if not row:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                "Não é possível excluir: não há outro usuário em usuarios_app para reatribuir "
                "os chamados vinculados (exigência da chave estrangeira no banco)."
            ),
        )
    return int(row[0])


def _reassign_chamados_before_delete_usuarios_app(
    db: Session, from_ua_id: int, to_ua_id: int
) -> None:
    """Move referências em `chamados` para outro solicitante/responsável (mesmo id em usuarios_app)."""
    if int(from_ua_id) == int(to_ua_id):
        return
    db.execute(
        text("UPDATE chamados SET solicitante_id = :t WHERE solicitante_id = :f"),
        {"f": int(from_ua_id), "t": int(to_ua_id)},
    )
    db.execute(
        text("UPDATE chamados SET responsavel_id = :t WHERE responsavel_id = :f"),
        {"f": int(from_ua_id), "t": int(to_ua_id)},
    )


def _safe_email_for_response(user: User) -> str:
    """
    Garante que o campo `email` que será retornado passa no validador `EmailStr`.
    Em Pydantic v2 não se usa `EmailStr(raw)` — isso falhava sempre e forçava `user{id}@example.com`.
    """
    raw = str(getattr(user, "email", "") or "").strip()
    if not raw:
        return f"user{int(user.id)}@example.com"
    try:
        TypeAdapter(EmailStr).validate_python(raw)
        return raw
    except Exception:
        return f"user{int(user.id)}@example.com"


def _user_schema_response(user: User) -> UserSchema:
    """Serializa usuário sem alterar o objeto ORM (evita e-mail sintético persistido por engano)."""
    return UserSchema.model_validate(user).model_copy(
        update={"email": _safe_email_for_response(user)}
    )


@router.get("/gerenciamento")
async def get_management_users(
    search: str = "",
    current_user: User = Depends(get_current_admin),
):
    """Lista usuários do Gerenciamento de Ativos (Snipe-IT)."""
    users = snipe_list_users(search=search or None)
    return {"data": users or []}


@router.get("/gerenciamento-diagnostico")
async def get_management_users_diagnosis(
    current_user: User = Depends(get_current_admin),
):
    """Diagnóstico da API de Gerenciamento de Ativos para troubleshooting."""
    return snipe_diagnose_api()


@router.get("", response_model=List[UserSchema])
async def get_users(
    skip: int = 0,
    limit: int = 100,
    role: Optional[str] = Query(
        None,
        description="Filtrar por perfil: admin, requester, technician, user, supervisor",
    ),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin)
):
    """Listar todos os usuários (apenas admin). Use `role=requester` para só cadastros do portal."""
    q = db.query(User)
    if role is not None and str(role).strip() != "":
        r = str(role).strip().lower()
        try:
            role_enum = UserRole(r)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Perfil inválido: {role}. Valores: admin, requester, technician, user, supervisor.",
            )
        # PostgreSQL: o tipo ENUM no banco usa rótulos em MAIÚSCULAS (ex.: ADMIN). Comparar com
        # User.role == UserRole.ADMIN gera bind 'admin' e falha (InvalidTextRepresentation).
        # Comparar via texto normalizado funciona em PG e SQLite.
        q = q.filter(func.lower(cast(User.role, String)) == role_enum.value)
    users = q.order_by(User.id.desc()).offset(skip).limit(limit).all()
    return [_user_schema_response(u) for u in users]

@router.get("/{user_id}", response_model=UserSchema)
async def get_user(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Obter usuário por ID"""
    # Usuário pode ver seu próprio perfil ou admin pode ver qualquer um
    if current_user.id != user_id and current_user.role != UserRole.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Acesso negado"
        )
    
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Usuário não encontrado"
        )
    return _user_schema_response(user)

def _create_requester_by_admin(db: Session, user_data: UserCreate) -> User:
    """Mesma lógica do cadastro público: telefone sem DDD + usuarios_app quando unificado."""
    from app.api.v1.endpoints import auth as auth_ep

    full_name = f"{user_data.first_name.strip()} {user_data.last_name.strip()}".strip()
    digits = auth_ep._full_phone_from_portal_local(user_data.phone)
    uname = auth_ep._portal_username_from_phone(digits)
    email_internal = auth_ep._portal_internal_email(digits)

    dup_phone = (
        db.query(User)
        .filter(User.phone == digits, User.role == UserRole.REQUESTER)
        .first()
    )
    if dup_phone:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Este telefone já está cadastrado.",
        )

    dup_email = db.query(User).filter(func.lower(User.email) == email_internal.lower()).first()
    if dup_email:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Este telefone já está cadastrado.",
        )

    usuario_app_id: int | None = None
    if auth_ep._is_postgres_unified() and _has_table(db, "usuarios_app"):
        exists_u = db.execute(
            text("SELECT id FROM usuarios_app WHERE lower(trim(username)) = :u LIMIT 1"),
            {"u": uname.lower()},
        ).first()
        if exists_u:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Este telefone já está cadastrado.",
            )
        usuario_app_id = auth_ep._insert_usuarios_app_portal(
            db,
            username=uname,
            nome=full_name,
            email=email_internal,
            password_plain=user_data.password,
        )

    new_user = User(
        name=full_name,
        email=email_internal,
        password_hash=get_password_hash(user_data.password),
        phone=digits,
        department=(user_data.department or "").strip() or None,
        role=UserRole.REQUESTER,
        is_active=True,
        snipe_user_id=usuario_app_id,
    )
    db.add(new_user)
    try:
        db.commit()
        db.refresh(new_user)
    except Exception as exc:
        from sqlalchemy.exc import IntegrityError, ProgrammingError

        try:
            db.rollback()
        except Exception:
            pass
        if isinstance(exc, IntegrityError):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Telefone ou e-mail interno já cadastrado (conflito no banco).",
            ) from exc
        if isinstance(exc, ProgrammingError):
            err_s = str(exc).lower()
            if "userrole" in err_s or "enum" in err_s:
                raise HTTPException(
                    status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                    detail="Execute as migrações do banco (alembic upgrade head) para incluir o perfil 'requester'.",
                ) from exc
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Não foi possível salvar o usuário: {exc!s}",
        ) from exc
    return new_user


@router.post("", response_model=UserSchema, status_code=status.HTTP_201_CREATED)
async def create_user(
    user_data: UserCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin)
):
    """Criar usuário: equipe (admin/técnico) ou usuário padrão (só abre chamado)."""
    if user_data.role == UserRole.REQUESTER:
        new_user = _create_requester_by_admin(db, user_data)
        return _user_schema_response(new_user)

    email_norm = user_data.email.strip().lower()
    existing_user = db.query(User).filter(func.lower(User.email) == email_norm).first()
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email já cadastrado",
        )

    new_user = User(
        name=user_data.name.strip(),
        email=user_data.email.strip(),
        password_hash=get_password_hash(user_data.password),
        phone=user_data.phone.strip() if user_data.phone else None,
        department=user_data.department.strip() if user_data.department else None,
        position=user_data.position.strip() if user_data.position else None,
        role=user_data.role,
        is_active=True,
    )

    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    return _user_schema_response(new_user)

@router.put("/{user_id}", response_model=UserSchema)
async def update_user(
    user_id: int,
    user_data: UserUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin)
):
    """Atualizar usuário (apenas admin)"""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Usuário não encontrado"
        )

    update_data = user_data.model_dump(exclude_unset=True)

    # E-mail: ignorar duplicidade do próprio usuário (antes bloqueava ao trocar/ajustar maiúsculas)
    if "email" in update_data and update_data["email"] is not None:
        new_email = (update_data["email"] or "").strip()
        old_email = (user.email or "").strip()
        if new_email.lower() != old_email.lower():
            dup = (
                db.query(User)
                .filter(
                    func.lower(User.email) == new_email.lower(),
                    User.id != user_id,
                )
                .first()
            )
            if dup:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Email já cadastrado",
                )
        update_data["email"] = new_email

    for field, value in update_data.items():
        setattr(user, field, value)

    db.commit()
    db.refresh(user)

    return _user_schema_response(user)


def _permanent_delete_user(db: Session, user_id: int, current_user: User) -> None:
    """
    Remove o registro de `users` e dependências no schema SQLAlchemy.
    No PostgreSQL unificado:
    - Bloqueia se existirem chamados **não finalizados** em `chamados` para este solicitante (usuarios_app).
    - Se não houver bloqueio, **reatribui** `solicitante_id`/`responsavel_id` dos chamados (inclusive encerrados)
      para outro `usuarios_app` antes de `DELETE`, pois a FK do banco impede apagar enquanto houver qualquer referência.
    """
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Usuário não encontrado",
        )
    if user.id == current_user.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Não é possível excluir seu próprio usuário",
        )

    uid_ua = user.snipe_user_id
    if _is_postgres_unified() and uid_ua and _has_table(db, "chamados"):
        # Só bloqueia se ainda houver chamados em aberto / em andamento (não encerrados).
        cnt = (
            db.execute(
                text(
                    """
                    SELECT COUNT(*) FROM chamados
                    WHERE solicitante_id = :sid
                      AND COALESCE(lower(trim(status::text)), '') NOT IN (
                          'resolved', 'closed', 'cancelled'
                      )
                    """
                ),
                {"sid": int(uid_ua)},
            ).scalar()
            or 0
        )
        if int(cnt) > 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=(
                    "Este usuário possui chamados em aberto ou em andamento no banco unificado. "
                    "Encerre ou cancele esses chamados (ou apenas desative o usuário). "
                    "Chamados já encerrados no histórico não impedem a exclusão."
                ),
            )

    try:
        # Dados ligados ao usuário (tickets SQLite / legado)
        db.query(Comment).filter(Comment.user_id == user_id).delete(synchronize_session=False)
        db.query(TicketHistory).filter(TicketHistory.user_id == user_id).delete(synchronize_session=False)
        db.query(Attachment).filter(Attachment.user_id == user_id).delete(synchronize_session=False)
        db.query(Notification).filter(Notification.user_id == user_id).delete(synchronize_session=False)

        db.query(OffboardingLog).filter(
            or_(
                OffboardingLog.user_id == user_id,
                OffboardingLog.created_by_id == user_id,
            )
        ).delete(synchronize_session=False)

        db.query(AssetAssignment).filter(
            or_(
                AssetAssignment.user_id == user_id,
                AssetAssignment.assigned_by_id == user_id,
            )
        ).delete(synchronize_session=False)

        req_tickets = db.query(Ticket).filter(Ticket.requester_id == user_id).all()
        for t in req_tickets:
            db.query(Notification).filter(Notification.ticket_id == t.id).delete(synchronize_session=False)
            db.delete(t)

        db.query(Ticket).filter(Ticket.assigned_technician_id == user_id).update(
            {Ticket.assigned_technician_id: None},
            synchronize_session=False,
        )

        ua_id = user.snipe_user_id
        db.delete(user)
        db.flush()

        if _is_postgres_unified() and ua_id and _has_table(db, "usuarios_app"):
            # FK `chamados_solicitante_id_fkey` (e responsável) impede DELETE enquanto houver qualquer linha,
            # inclusive encerradas — reatribui para outro usuarios_app antes de apagar.
            keeper_ua = _pick_keeper_usuarios_app_id(db, int(ua_id))
            if _has_table(db, "chamados"):
                _reassign_chamados_before_delete_usuarios_app(db, int(ua_id), keeper_ua)
            db.execute(text("DELETE FROM usuarios_app WHERE id = :id"), {"id": int(ua_id)})

        db.commit()
    except Exception as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Não foi possível excluir permanentemente: {exc!s}",
        ) from exc


@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_user(
    user_id: int,
    permanent: bool = False,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin),
):
    """
    Excluir usuário (apenas admin).
    - `permanent=false` (padrão): apenas **inativa** (`is_active=False`).
    - `permanent=true`: **remove** o registro do banco e dependências (e `usuarios_app` quando aplicável).
    """
    if not permanent:
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Usuário não encontrado",
            )
        if user.id == current_user.id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Não é possível desativar seu próprio usuário",
            )
        user.is_active = False
        db.commit()
        return None

    _permanent_delete_user(db, user_id, current_user)
    return None

@router.put("/{user_id}/password")
async def update_user_password(
    user_id: int,
    password_data: UserPasswordUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Atualizar senha do usuário"""
    # Usuário pode alterar sua própria senha ou admin pode alterar qualquer senha
    if current_user.id != user_id and current_user.role != UserRole.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Acesso negado"
        )
    
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Usuário não encontrado"
        )
    
    # Se não for admin, verificar senha atual
    if current_user.role != UserRole.ADMIN:
        from app.core.security import verify_password
        if not verify_password(password_data.current_password, user.password_hash):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Senha atual incorreta"
            )
    
    # Atualizar senha (bcrypt em users)
    user.password_hash = get_password_hash(password_data.new_password)

    # Portal (requester): login principal usa usuarios_app (hash Telefones)
    if (
        user.role == UserRole.REQUESTER
        and user.snipe_user_id is not None
        and _is_postgres_unified()
        and _has_table(db, "usuarios_app")
    ):
        salt = secrets.token_hex(16)
        ph = hash_password_telefones_style(password_data.new_password, salt)
        db.execute(
            text("UPDATE usuarios_app SET password_hash = :ph, salt = :salt WHERE id = :id"),
            {"ph": ph, "salt": salt, "id": int(user.snipe_user_id)},
        )

    db.commit()

    return {"message": "Senha atualizada com sucesso"}

