from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import RedirectResponse
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from sqlalchemy import text, func
from sqlalchemy.exc import IntegrityError, OperationalError, ProgrammingError
from datetime import datetime, timezone
import logging
import hashlib
import re
import secrets
import unicodedata
from app.core.database import get_db
from app.core.security import (
    verify_password,
    get_password_hash,
    create_access_token,
    create_refresh_token,
    decode_token,
)
from app.core.config import settings
from app.core.telefones_auth import verify_password_telefones, hash_password_telefones_style
from app.models.user import User, UserRole
from app.schemas.auth import Token, LoginRequest, RefreshTokenRequest, SSOExchangeRequest, OIDCExchangeRequest, PortalRegisterRequest
from app.api.v1.dependencies import get_current_user
from sqlalchemy import inspect as sa_inspect

logger = logging.getLogger(__name__)

router = APIRouter()
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login")

_LOGIN_INCORRECT_DETAIL = (
    "E-mail/usuário ou senha incorretos. "
    "Use a senha do Gerenciamento de Telefones ou a senha que você definiu neste sistema (Chamados)."
)


def _safe_verify_bcrypt(plain: str, hashed) -> bool:
    if not plain or not hashed or not str(hashed).strip():
        return False
    try:
        return verify_password(plain, hashed)
    except Exception:
        return False


def _is_postgres_unified() -> bool:
    u = str(settings.DATABASE_URL or "")
    return u.startswith("postgresql") or "postgres" in u.lower()


def _has_table(db: Session, name: str) -> bool:
    try:
        return name in sa_inspect(db.get_bind()).get_table_names()
    except Exception:
        return False


def _only_digits(s: str) -> str:
    return re.sub(r"\D", "", s or "")


def _normalize_login_identifier(s: str) -> str:
    """Minúsculas, espaços colapsados, NFC — alinha digitação com username/e-mail/nome no banco."""
    t = (s or "").strip()
    t = " ".join(t.split())
    try:
        t = unicodedata.normalize("NFC", t)
    except Exception:
        pass
    return t.lower()


def _lookup_usuarios_app_login_row(db: Session, cand: str):
    """
    Busca em usuarios_app por e-mail, depois username, depois nome_exibicao.
    Queries simples (sem ORDER BY CASE) evitam erro em alguns PostgreSQL; nome_exibicao é opcional.
    """
    cols = "id, username, email, nome_exibicao, password_hash, salt, is_admin, ativo"

    def _one(sql: str, params: dict):
        return db.execute(text(sql), params).mappings().first()

    r = _one(
        f"""
        SELECT {cols} FROM usuarios_app
        WHERE lower(trim(coalesce(email, ''))) = :login
        LIMIT 1
        """,
        {"login": cand},
    )
    if r:
        return r
    r = _one(
        f"""
        SELECT {cols} FROM usuarios_app
        WHERE lower(trim(username)) = :login
        LIMIT 1
        """,
        {"login": cand},
    )
    if r:
        return r
    try:
        r = _one(
            f"""
            SELECT {cols} FROM usuarios_app
            WHERE lower(trim(coalesce(nome_exibicao, ''))) = :login
            LIMIT 1
            """,
            {"login": cand},
        )
    except ProgrammingError as e:
        logger.warning("login: nome_exibicao indisponível ou query inválida: %s", e)
        db.rollback()
        return None
    return r


def _portal_username_from_phone(digits: str) -> str:
    return f"portal_{digits}"


def _portal_internal_email(digits: str) -> str:
    """E-mail sintético legado (cadastro antigo por telefone). Mantido para admin criar requester por telefone."""
    return f"portal+{digits}@example.com"


def _portal_username_from_email(email: str) -> str:
    """Username estável e único em `usuarios_app` para cadastro portal por e-mail."""
    e = (email or "").strip().lower()
    h = hashlib.sha256(e.encode("utf-8")).hexdigest()[:20]
    return f"portal_{h}"


def _portal_default_ddd_digits() -> str:
    d = _only_digits(settings.PORTAL_DEFAULT_DDD)
    if len(d) == 2:
        return d
    return "11"


def _full_phone_from_portal_local(local: str) -> str:
    """Concatena DDD padrão (PORTAL_DEFAULT_DDD) + número local sem DDD."""
    loc = _only_digits(local)
    if len(loc) < 8 or len(loc) > 9:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Telefone sem DDD deve ter 8 ou 9 dígitos.",
        )
    return _portal_default_ddd_digits() + loc


def _insert_usuarios_app_portal(
    db: Session,
    *,
    username: str,
    nome: str,
    email: str,
    password_plain: str,
) -> int:
    """Cria linha em usuarios_app (senha no formato Telefones) para FK em chamados.solicitante_id."""
    salt = secrets.token_hex(16)
    ph = hash_password_telefones_style(password_plain, salt)
    try:
        r = db.execute(
            text(
                """
                INSERT INTO usuarios_app (username, email, nome_exibicao, password_hash, salt, is_admin, ativo)
                VALUES (:username, :email, :nome, :ph, :salt, false, true)
                RETURNING id
                """
            ),
            {"username": username, "email": email, "nome": nome, "ph": ph, "salt": salt},
        )
        row = r.first()
        if row is not None:
            return int(row[0])
    except Exception as exc:
        try:
            db.rollback()
        except Exception:
            pass
        msg = "Não foi possível concluir o cadastro no banco unificado (usuarios_app). Contate o TI."
        if settings.DEBUG:
            msg = f"{msg} Detalhe: {exc!s}"
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=msg,
        ) from exc
    raise HTTPException(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        detail="Falha ao obter id do usuário criado.",
    )


def _resolve_email_for_chamados_user(user_row: dict) -> str:
    """Garante e-mail válido para o modelo User (Pydantic/API)."""
    email = user_row.get("email") or None
    uid = int(user_row.get("id") or 0)

    def _sanitize_email(raw: str) -> str:
        e = str(raw or "").strip()
        return re.sub(r"\s+", "", e)

    def _make_sso_email() -> str:
        username_raw = str(user_row.get("username") or "user").strip().lower()
        username_slug = re.sub(r"\s+", "", username_raw)
        username_slug = re.sub(r"[^a-z0-9._-]", "", username_slug)
        if not username_slug:
            username_slug = "user"
        # Inclui id do usuarios_app para nunca colidir com outro login (UNIQUE em users.email)
        return f"{username_slug}.u{uid}@example.com"

    if not email:
        email = _make_sso_email()
    else:
        email = _sanitize_email(email)
        if not email or "@" not in email or email.lower().endswith("@sso.local"):
            email = _make_sso_email()
    return email


def _bump_conflicting_email(db: Session, email: str, *, except_user_id: int | None) -> None:
    """Libera `email` na tabela users: quem já tinha esse e-mail recebe endereço reservado."""
    if not (email or "").strip():
        return
    em = email.strip().lower()
    q = db.query(User).filter(func.lower(User.email) == em)
    if except_user_id is not None:
        q = q.filter(User.id != except_user_id)
    for other in q.all():
        other.email = f"legacy.uid{other.id}.merge@example.com"
    db.flush()


def upsert_chamados_user_from_usuario_app(
    db: Session,
    user_row: dict,
    *,
    usuario_id: int | None = None,
) -> User:
    """
    Mantém a tabela `users` (chamados) alinhada ao cadastro do Gerenciamento (`usuarios_app`).
    `snipe_user_id` guarda o id em usuarios_app (reuso histórico de campo).
    """
    uid = usuario_id if usuario_id is not None else int(user_row["id"])
    email = _resolve_email_for_chamados_user({**user_row, "id": uid})
    role = UserRole.ADMIN if bool(user_row.get("is_admin")) else UserRole.USER

    user = db.query(User).filter(User.snipe_user_id == uid).first()
    if user is None:
        user = db.query(User).filter(User.email == email).first()

    if user is not None and user.role == UserRole.REQUESTER:
        # Cadastro pelo portal: mantém acesso restrito mesmo após sync com usuarios_app
        role = UserRole.REQUESTER

    if user is None:
        _bump_conflicting_email(db, email, except_user_id=None)

        user = User(
            name=user_row.get("nome_exibicao") or user_row.get("username") or "Usuário",
            email=email,
            password_hash=get_password_hash(secrets.token_urlsafe(32)),
            role=role,
            is_active=True,
            snipe_user_id=uid,
        )
        db.add(user)
        db.flush()
    else:
        user.name = user_row.get("nome_exibicao") or user_row.get("username") or user.name
        _bump_conflicting_email(db, email, except_user_id=user.id)
        user.email = email
        user.role = role
        user.is_active = True
        user.snipe_user_id = uid
    return user


@router.post("/register-portal", status_code=status.HTTP_201_CREATED)
async def register_portal(
    body: PortalRegisterRequest,
    db: Session = Depends(get_db),
):
    """
    Cadastro público (link compartilhado): nome, sobrenome, e-mail, setor e senha.
    Cria usuário com papel `requester` (acesso apenas à página de abrir chamado).
    Com PostgreSQL + `usuarios_app`, também insere lá para manter FK dos chamados.
    """
    if body.password != body.password_confirm:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="As senhas não conferem.",
        )

    full_name = f"{body.first_name.strip()} {body.last_name.strip()}".strip()
    if len(full_name) < 3:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Preencha nome e sobrenome.",
        )

    email_norm = str(body.email).strip().lower()

    dup_email = db.query(User).filter(func.lower(User.email) == email_norm).first()
    if dup_email:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Este e-mail já está cadastrado.",
        )

    uname = _portal_username_from_email(email_norm)

    usuario_app_id: int | None = None
    if _is_postgres_unified() and _has_table(db, "usuarios_app"):
        exists_u = db.execute(
            text(
                """
                SELECT id FROM usuarios_app
                WHERE lower(trim(username)) = :u OR lower(trim(coalesce(email, ''))) = :e
                LIMIT 1
                """
            ),
            {"u": uname.lower(), "e": email_norm},
        ).first()
        if exists_u:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Este e-mail já está cadastrado.",
            )
        usuario_app_id = _insert_usuarios_app_portal(
            db,
            username=uname,
            nome=full_name,
            email=email_norm,
            password_plain=body.password,
        )

    new_user = User(
        name=full_name,
        email=email_norm,
        password_hash=get_password_hash(body.password),
        phone=None,
        department=(body.department or "").strip() or None,
        role=UserRole.REQUESTER,
        is_active=True,
        snipe_user_id=usuario_app_id,
    )
    db.add(new_user)
    try:
        db.commit()
        db.refresh(new_user)
    except IntegrityError as exc:
        try:
            db.rollback()
        except Exception:
            pass
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Este e-mail já está cadastrado ou há conflito no banco.",
        ) from exc
    except ProgrammingError as exc:
        try:
            db.rollback()
        except Exception:
            pass
        err_s = str(exc).lower()
        if "userrole" in err_s or "enum" in err_s:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Execute as migrações do banco (alembic upgrade head) para incluir o perfil 'requester'.",
            ) from exc
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Não foi possível salvar o cadastro: {exc!s}",
        ) from exc
    except Exception as exc:
        try:
            db.rollback()
        except Exception:
            pass
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Não foi possível salvar o cadastro: {exc!s}",
        ) from exc

    return {
        "message": "Cadastro realizado. Use seu e-mail e senha para entrar na área de abrir chamado.",
        "user_id": new_user.id,
    }


@router.post("/login", response_model=Token)
async def login(
    login_data: LoginRequest,
    db: Session = Depends(get_db)
):
    """
    Autenticação:
    - **Banco único (PostgreSQL + `usuarios_app`)**: mesmo usuário/senha do Gerenciamento de Telefones
      (login = e-mail ou nome de usuário).
    - **Legado**: tabela `users` com hash bcrypt (ex.: SQLite antigo).
    """
    identifier_raw = (login_data.email or "").strip()
    identifier_lower = _normalize_login_identifier(identifier_raw)
    login_candidates = [identifier_lower]
    # E-mail completo não bateu username; muitos cadastros só têm login "suporte" sem coluna email preenchida
    if "@" in identifier_lower:
        local_part = identifier_lower.split("@", 1)[0].strip()
        if local_part:
            login_candidates.append(local_part)
    digits = _only_digits(identifier_raw)
    if len(digits) >= 10:
        login_candidates.append(_portal_username_from_phone(digits).lower())
    # Cadastro portal: usuário pode digitar só o número local (sem DDD)
    if 8 <= len(digits) <= 9:
        dd = _portal_default_ddd_digits()
        login_candidates.append(_portal_username_from_phone(dd + digits).lower())
    login_candidates = list(dict.fromkeys(login_candidates))

    # 0) E-mail explícito: tenta primeiro bcrypt em `users` (senha definida no Chamados).
    #    Assim quem atualizou só a senha aqui não fica "preso" na validação do Gerenciamento (Telefones).
    if "@" in identifier_lower:
        u_chamados = (
            db.query(User)
            .filter(func.lower(User.email) == identifier_lower)
            .first()
        )
        if u_chamados is not None and _safe_verify_bcrypt(
            login_data.password, u_chamados.password_hash
        ):
            if not u_chamados.is_active:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Usuário inativo",
                )
            u_chamados.last_login = datetime.now(timezone.utc)
            db.commit()
            db.refresh(u_chamados)
            access_token = create_access_token(
                data={
                    "sub": str(u_chamados.id),
                    "email": u_chamados.email,
                    "role": u_chamados.role.value,
                }
            )
            refresh_token = create_refresh_token(
                data={"sub": str(u_chamados.id), "email": u_chamados.email}
            )
            return {
                "access_token": access_token,
                "refresh_token": refresh_token,
                "token_type": "bearer",
            }

    # 1) Fonte única: usuarios_app (senha SHA256+salt igual ao Streamlit)
    row = None
    if _is_postgres_unified() and _has_table(db, "usuarios_app"):
        for cand in login_candidates:
            row = _lookup_usuarios_app_login_row(db, cand)
            if row:
                break

        if row:
            if not bool(row.get("ativo")):
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Usuário inativo",
                )
            ua_id = int(row["id"])
            telefones_ok = verify_password_telefones(
                login_data.password,
                str(row.get("password_hash") or ""),
                str(row.get("salt") or ""),
            )
            if telefones_ok:
                user = upsert_chamados_user_from_usuario_app(db, dict(row))
                user.last_login = datetime.now(timezone.utc)
                db.commit()
                db.refresh(user)
                access_token = create_access_token(
                    data={"sub": str(user.id), "email": user.email, "role": user.role.value}
                )
                refresh_token = create_refresh_token(
                    data={"sub": str(user.id), "email": user.email}
                )
                return {
                    "access_token": access_token,
                    "refresh_token": refresh_token,
                    "token_type": "bearer",
                }

            # Mesmo login encontrado em usuarios_app, mas senha não bate no formato Telefones:
            # permite entrar com a senha do painel (bcrypt em `users`), ex.: admin alterou só no Chamados.
            cand_users: list[User] = []
            by_snipe = db.query(User).filter(User.snipe_user_id == ua_id).first()
            if by_snipe:
                cand_users.append(by_snipe)
            by_email = (
                db.query(User)
                .filter(func.lower(User.email) == identifier_lower)
                .first()
            )
            if by_email and by_email not in cand_users:
                cand_users.append(by_email)
            for u in cand_users:
                if _safe_verify_bcrypt(login_data.password, u.password_hash):
                    u.last_login = datetime.now(timezone.utc)
                    db.commit()
                    db.refresh(u)
                    access_token = create_access_token(
                        data={"sub": str(u.id), "email": u.email, "role": u.role.value}
                    )
                    refresh_token = create_refresh_token(
                        data={"sub": str(u.id), "email": u.email}
                    )
                    return {
                        "access_token": access_token,
                        "refresh_token": refresh_token,
                        "token_type": "bearer",
                    }
            # Senha incorreta para Telefones e para bcrypt: segue para o passo 2 (conta só em users, etc.)

    # 2) Tabela users (bcrypt): e-mail ou telefone (cadastro portal)
    user = (
        db.query(User)
        .filter(func.lower(User.email) == identifier_lower)
        .first()
    )
    # Digitou e-mail corporativo, mas em `users` o e-mail veio sintético (@example.com) — acha pelo username em usuarios_app
    if user is None and "@" in identifier_lower:
        local_part = identifier_lower.split("@", 1)[0].strip()
        if local_part and _is_postgres_unified() and _has_table(db, "usuarios_app"):
            try:
                row_uid = db.execute(
                    text(
                        """
                        SELECT u.id
                        FROM users u
                        INNER JOIN usuarios_app ua ON ua.id = u.snipe_user_id
                        WHERE lower(trim(ua.username)) = :local
                        LIMIT 1
                        """
                    ),
                    {"local": local_part},
                ).first()
                if row_uid is not None:
                    user = db.query(User).filter(User.id == int(row_uid[0])).first()
            except (ProgrammingError, OperationalError) as e:
                logger.warning("login: join users/usuarios_app falhou: %s", e)
                db.rollback()
    if user is None and len(digits) >= 10:
        user = (
            db.query(User)
            .filter(User.phone == digits, User.role == UserRole.REQUESTER)
            .first()
        )
    if user is None and 8 <= len(digits) <= 9:
        full_digits = _portal_default_ddd_digits() + digits
        user = (
            db.query(User)
            .filter(User.phone == full_digits, User.role == UserRole.REQUESTER)
            .first()
        )

    if not user or not _safe_verify_bcrypt(login_data.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=_LOGIN_INCORRECT_DETAIL,
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Usuário inativo",
        )

    user.last_login = datetime.now(timezone.utc)
    db.commit()

    access_token = create_access_token(
        data={"sub": str(user.id), "email": user.email, "role": user.role.value}
    )
    refresh_token = create_refresh_token(
        data={"sub": str(user.id), "email": user.email}
    )

    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer",
    }

@router.post("/refresh", response_model=Token)
async def refresh_token(
    refresh_data: RefreshTokenRequest,
    db: Session = Depends(get_db)
):
    """Renovar token de acesso usando refresh token"""
    payload = decode_token(refresh_data.refresh_token)
    
    if not payload or payload.get("type") != "refresh":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token inválido"
        )
    
    user_id = payload.get("sub")
    user = db.query(User).filter(User.id == int(user_id)).first()
    
    if not user or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Usuário não encontrado ou inativo"
        )
    
    # Criar novos tokens
    access_token = create_access_token(
        data={"sub": str(user.id), "email": user.email, "role": user.role.value}
    )
    refresh_token = create_refresh_token(
        data={"sub": str(user.id), "email": user.email}
    )
    
    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer"
    }

@router.get("/me")
async def get_current_user_info(
    current_user: User = Depends(get_current_user)
):
    """Retorna informações do usuário autenticado"""
    from app.schemas.user import User as UserSchema
    return UserSchema.model_validate(current_user)


@router.post("/sso-exchange", response_model=Token)
async def sso_exchange(
    payload: SSOExchangeRequest,
    db: Session = Depends(get_db),
):
    """
    Troca `sso_code` (1 uso) por JWTs no formato que o React já espera.

    Observacao:
    - Este endpoint garante que um usuario do schema antigo (`usuarios_app`)
      exista na tabela `users` que o backend usa para autenticar.
    """
    code = str(payload.sso_code or "").strip()
    if not code:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="sso_code e obrigatorio")

    # Debug para entender 401 (não vaza o token inteiro no log).
    code_preview = f"{code[:8]}...{code[-4:]}" if len(code) > 12 else code
    now_dbg = datetime.now(timezone.utc)
    print(f"[SSO] sso-exchange recebido: {code_preview} em {now_dbg.isoformat()}")

    # Diagnostico (sem atualizar ainda): valida se existe, se ja foi usado e se esta expirado.
    row = db.execute(
        text(
            """
            SELECT usuario_id, usado_em, expira_em
            FROM sso_codes
            WHERE code = :code
            LIMIT 1
            """
        ),
        {"code": code},
    ).mappings().first()

    if row:
        print(
            "[SSO] estado no banco:",
            f"usuario_id={row.get('usuario_id')},",
            f"usado_em={row.get('usado_em')},",
            f"expira_em={row.get('expira_em')}",
        )
    else:
        print("[SSO] estado no banco: sso_code nao encontrado")

    if not row:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="sso_code nao encontrado")

    expira_em = row.get("expira_em")
    usado_em = row.get("usado_em")
    now_utc = datetime.now(timezone.utc)

    # Expiracao
    if expira_em is not None:
        try:
            if expira_em <= now_utc:
                raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="sso_code expirado")
        except TypeError:
            # se nao der pra comparar (timezone), cai no caso conservador via SQL
            expira_ok = db.execute(
                text("SELECT 1 FROM sso_codes WHERE code = :code AND expira_em > NOW() LIMIT 1"),
                {"code": code},
            ).first()
            if not expira_ok:
                raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="sso_code expirado")

    # Se ja foi usado, permitimos reemissao apenas quando for duplicacao "instantanea"
    # Importante (modo robusto):
    # - Mesmo que `usado_em` já tenha sido preenchido (code reusado/duplicado por navegação),
    #   ainda permitimos a troca enquanto não expirou.
    # - Isso evita travar o usuário quando o navegador tenta o sso-exchange mais de uma vez.
    usuario_id = row.get("usuario_id")

    updated = db.execute(
        text(
            """
            UPDATE sso_codes
            SET usado_em = NOW()
            WHERE code = :code
              AND usado_em IS NULL
              AND expira_em > NOW()
            """
        ),
        {"code": code},
    )
    # `updated` nao eh usado; apenas garante que se ainda estava 'livre' marcamos.

    # Buscar dados do usuario no schema unificado.
    user_row = db.execute(
        text(
            """
            SELECT id, username, email, nome_exibicao, is_admin, ativo
            FROM usuarios_app
            WHERE id = :id
            LIMIT 1
            """
        ),
        {"id": usuario_id},
    ).mappings().first()

    if not user_row:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Usuario nao encontrado")

    if not bool(user_row.get("ativo")):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Usuario inativo")

    user = upsert_chamados_user_from_usuario_app(db, dict(user_row))
    db.commit()
    db.refresh(user)

    access_token = create_access_token(
        data={"sub": str(user.id), "email": user.email, "role": user.role.value}
    )
    refresh_token = create_refresh_token(data={"sub": str(user.id), "email": user.email})

    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer",
    }


def _lookup_usuario_app_from_oidc(db: Session, userinfo: dict) -> dict | None:
    email = str(userinfo.get("email") or "").strip().lower()
    username = str(userinfo.get("preferred_username") or userinfo.get("username") or "").strip().lower()
    candidates = [c for c in {email, username} if c]
    if not candidates or not _has_table(db, "usuarios_app"):
        return None
    for cand in candidates:
        row = _lookup_usuarios_app_login_row(db, cand)
        if row:
            return dict(row)
    return None


@router.get("/oidc/status")
async def oidc_status():
    from app.services.oidc import public_config

    return public_config()


@router.get("/oidc/login")
async def oidc_login():
    from app.services.oidc import build_login_redirect, oidc_enabled

    if not oidc_enabled():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="OIDC desabilitado")
    url, _state = build_login_redirect()
    return RedirectResponse(url=url, status_code=302)


@router.get("/oidc/callback")
async def oidc_callback(
    code: str = "",
    state: str = "",
    db: Session = Depends(get_db),
):
    from app.services.oidc import (
        exchange_authorization_code,
        fetch_userinfo,
        oidc_enabled,
        store_jwt_exchange,
        verify_state,
    )

    if not oidc_enabled():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="OIDC desabilitado")
    if not code or not state or not verify_state(state):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="State OIDC invalido")

    try:
        token_payload = exchange_authorization_code(code)
        userinfo = fetch_userinfo(str(token_payload.get("access_token") or ""))
    except Exception as exc:
        logger.warning("OIDC callback falhou: %s", exc)
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Falha OIDC") from exc

    user_row = _lookup_usuario_app_from_oidc(db, userinfo)
    if not user_row:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Usuario OIDC nao encontrado em usuarios_app. Cadastre ou sincronize antes.",
        )
    if not bool(user_row.get("ativo", True)):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Usuario inativo")

    user = upsert_chamados_user_from_usuario_app(db, user_row)
    db.commit()
    db.refresh(user)

    access_token = create_access_token(
        data={"sub": str(user.id), "email": user.email, "role": user.role.value}
    )
    refresh_token = create_refresh_token(data={"sub": str(user.id), "email": user.email})
    exchange_code = store_jwt_exchange(access_token, refresh_token)
    db.commit()

    front = settings.FRONTEND_URL.rstrip("/")
    return RedirectResponse(url=f"{front}/login?oidc_code={exchange_code}", status_code=302)


@router.post("/oidc/exchange", response_model=Token)
async def oidc_exchange(payload: OIDCExchangeRequest):
    from app.services.oidc import oidc_enabled, pop_jwt_exchange

    if not oidc_enabled():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="OIDC desabilitado")
    tokens = pop_jwt_exchange(str(payload.oidc_code or "").strip())
    if not tokens:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="oidc_code invalido ou expirado")
    return {
        "access_token": tokens["access_token"],
        "refresh_token": tokens["refresh_token"],
        "token_type": "bearer",
    }


@router.get("/oidc/logout-url")
async def oidc_logout_url():
    from app.services.oidc import logout_url, oidc_enabled

    if not oidc_enabled():
        return {"enabled": False, "url": ""}
    return {"enabled": True, "url": logout_url()}

