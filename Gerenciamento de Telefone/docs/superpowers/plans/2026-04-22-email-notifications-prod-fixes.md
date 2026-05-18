# Email Notifications + Reset de Senha Admin + Fixes de Produção

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended)
> or superpowers:executing-plans. Steps use checkbox (`- [ ]`) syntax.

**Goal:** Adicionar reset de senha por e-mail para admins, notificações de chamado aberto e corrigir todos os gaps de segurança para produção.

**Architecture:** Serviço SMTP centralizado em `src/services/email_service.py` compartilhado por Streamlit e FastAPI. Reset de senha via token 1-uso em PostgreSQL. Notificação de chamado hookada em `criar_chamado()` no repository. Fixes de produção isolados em arquivos específicos.

**Tech Stack:** Python 3.10+, smtplib nativo, STARTTLS, psycopg, Streamlit, FastAPI, PostgreSQL

---

## Mapa de Arquivos

| Ação | Arquivo | Propósito |
|------|---------|-----------|
| Criar | `src/services/__init__.py` | Pacote services |
| Criar | `src/services/email_service.py` | SMTP client compartilhado |
| Modificar | `src/db/migrations.py` | Tabela password_reset_tokens |
| Modificar | `src/db/repository.py` | Funções reset + listar admins + hook chamado |
| Modificar | `app.py` | UI reset senha na tela de login |
| Modificar | `Sistema de Chamados TI/backend/app/api/v1/endpoints/telefones.py` | Fix exception leakage |
| Modificar | `Sistema de Chamados TI/backend/app/api/v1/endpoints/auth.py` | Fix exception leakage + JWT_SECRET |
| Modificar | `Sistema de Chamados TI/backend/app/api/deps.py` | Fix JWT_SECRET obrigatório |
| Modificar | `src/pages/config_admin.py` | Senha mínima 8 chars |
| Modificar | `.env.example` | Variáveis SMTP |
| Mover | `scripts/migrate_sqlite_to_postgres.py` → `scripts/archive/` | Arquivar script de migração |

---

## Task 1: Serviço de E-mail Compartilhado

**Files:**
- Criar: `src/services/__init__.py`
- Criar: `src/services/email_service.py`

- [ ] **Step 1: Criar `src/services/__init__.py`**

```python
```
(arquivo vazio)

- [ ] **Step 2: Criar `src/services/email_service.py`**

```python
"""Serviço SMTP centralizado. Usado por Streamlit e FastAPI."""
from __future__ import annotations

import logging
import os
import smtplib
import time
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import Optional

logger = logging.getLogger(__name__)

_MAX_RETRIES = 3
_RETRY_DELAY = 2  # segundos entre tentativas


def _smtp_config() -> dict:
    return {
        "host": os.environ.get("SMTP_HOST", "email.locaweb.com.br").strip(),
        "port": int(os.environ.get("SMTP_PORT", "587")),
        "user": os.environ.get("SMTP_USER", "").strip(),
        "password": os.environ.get("SMTP_PASSWORD", "").strip(),
        "from_addr": os.environ.get("SMTP_FROM", os.environ.get("SMTP_USER", "")).strip(),
    }


def send_email(
    to: str | list[str],
    subject: str,
    body_html: str,
    body_text: Optional[str] = None,
) -> bool:
    """
    Envia e-mail via SMTP Locaweb com STARTTLS.
    Retorna True se enviado, False se falhou (falha silenciosa — não quebra fluxo).
    """
    cfg = _smtp_config()
    if not cfg["user"] or not cfg["password"]:
        logger.warning("SMTP não configurado — e-mail não enviado.")
        return False

    recipients = [to] if isinstance(to, str) else to
    recipients = [r.strip() for r in recipients if r and r.strip()]
    if not recipients:
        return False

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = cfg["from_addr"]
    msg["To"] = ", ".join(recipients)

    if body_text:
        msg.attach(MIMEText(body_text, "plain", "utf-8"))
    msg.attach(MIMEText(body_html, "html", "utf-8"))

    for attempt in range(1, _MAX_RETRIES + 1):
        try:
            with smtplib.SMTP(cfg["host"], cfg["port"], timeout=15) as server:
                server.ehlo()
                server.starttls()
                server.ehlo()
                server.login(cfg["user"], cfg["password"])
                server.sendmail(cfg["from_addr"], recipients, msg.as_string())
            logger.info("E-mail enviado para %s", recipients)
            return True
        except Exception as exc:
            logger.warning("Tentativa %d/%d falhou: %s", attempt, _MAX_RETRIES, exc)
            if attempt < _MAX_RETRIES:
                time.sleep(_RETRY_DELAY)

    logger.error("Falha ao enviar e-mail para %s após %d tentativas.", recipients, _MAX_RETRIES)
    return False


def send_reset_email(to: str, reset_url: str) -> bool:
    """Envia e-mail de reset de senha para admin."""
    subject = "Redefinição de senha — Gerenciamento de Telefones"
    body_html = f"""
    <html><body style="font-family:Arial,sans-serif;color:#222;">
    <h2 style="color:#111827;">Redefinição de senha</h2>
    <p>Você solicitou a redefinição da sua senha de administrador.</p>
    <p>Clique no botão abaixo para criar uma nova senha. O link é válido por <strong>1 hora</strong> e pode ser usado apenas uma vez.</p>
    <p style="margin:24px 0;">
        <a href="{reset_url}" style="background:#f2c230;color:#111827;padding:12px 24px;
           border-radius:6px;text-decoration:none;font-weight:700;">
           Redefinir minha senha
        </a>
    </p>
    <p style="color:#666;font-size:0.85em;">Se você não solicitou este e-mail, ignore-o. Sua senha não será alterada.</p>
    <hr style="border:none;border-top:1px solid #eee;margin:24px 0;">
    <p style="color:#999;font-size:0.8em;">Prosper Distribuidora — Sistema de Gerenciamento de Telefones</p>
    </body></html>
    """
    body_text = f"Redefinição de senha\n\nAcesse o link abaixo (válido por 1 hora):\n{reset_url}\n\nSe não solicitou, ignore este e-mail."
    return send_email(to, subject, body_html, body_text)


def send_chamado_notification(
    admins_emails: list[str],
    numero_chamado: str,
    titulo: str,
    solicitante: str,
    aberto_em: str,
    descricao: str = "",
) -> bool:
    """Notifica admins quando novo chamado é aberto."""
    subject = f"[Chamado #{numero_chamado}] {titulo}"
    desc_html = f"<p><strong>Descrição:</strong> {descricao}</p>" if descricao else ""
    body_html = f"""
    <html><body style="font-family:Arial,sans-serif;color:#222;">
    <h2 style="color:#111827;">Novo chamado aberto</h2>
    <table style="border-collapse:collapse;width:100%;max-width:600px;">
      <tr><td style="padding:8px;border-bottom:1px solid #eee;color:#666;width:140px;">Número</td>
          <td style="padding:8px;border-bottom:1px solid #eee;font-weight:600;">#{numero_chamado}</td></tr>
      <tr><td style="padding:8px;border-bottom:1px solid #eee;color:#666;">Título</td>
          <td style="padding:8px;border-bottom:1px solid #eee;">{titulo}</td></tr>
      <tr><td style="padding:8px;border-bottom:1px solid #eee;color:#666;">Solicitante</td>
          <td style="padding:8px;border-bottom:1px solid #eee;">{solicitante}</td></tr>
      <tr><td style="padding:8px;color:#666;">Aberto em</td>
          <td style="padding:8px;">{aberto_em}</td></tr>
    </table>
    {desc_html}
    <hr style="border:none;border-top:1px solid #eee;margin:24px 0;">
    <p style="color:#999;font-size:0.8em;">Prosper Distribuidora — Sistema de Chamados TI</p>
    </body></html>
    """
    return send_email(admins_emails, subject, body_html)
```

- [ ] **Step 3: Verificar importação**

```bash
cd "C:\Users\TI02\Desktop\Planilhas Telefones"
python -c "from src.services.email_service import send_email; print('OK')"
```
Esperado: `OK`

- [ ] **Step 4: Commit**

```bash
git add src/services/__init__.py src/services/email_service.py
git commit -m "feat(email): add shared SMTP email service with retry and HTML templates"
```

---

## Task 2: Migration — Tabela password_reset_tokens

**Files:**
- Modificar: `src/db/migrations.py`

- [ ] **Step 1: Adicionar `_create_password_reset_tokens` em `src/db/migrations.py`**

Localizar o final da função `run_migrations` e adicionar a chamada:

```python
# Em run_migrations(), adicionar após _create_line_flags(conn):
_create_password_reset_tokens(conn)
```

Adicionar a função no final do arquivo:

```python
def _create_password_reset_tokens(conn) -> None:
    conn.execute("""
        CREATE TABLE IF NOT EXISTS password_reset_tokens (
            id SERIAL PRIMARY KEY,
            usuario_id INTEGER NOT NULL,
            token VARCHAR(64) NOT NULL UNIQUE,
            expira_em TIMESTAMPTZ NOT NULL,
            usado_em TIMESTAMPTZ,
            criado_em TIMESTAMPTZ NOT NULL DEFAULT NOW()
        )
    """)
    conn.execute("""
        CREATE INDEX IF NOT EXISTS idx_reset_tokens_token
        ON password_reset_tokens(token)
        WHERE usado_em IS NULL
    """)
```

- [ ] **Step 2: Rodar migration**

```bash
cd "C:\Users\TI02\Desktop\Planilhas Telefones"
python -c "from src.db.repository import init_db; init_db(); print('OK')"
```
Esperado: `OK` sem erros.

- [ ] **Step 3: Commit**

```bash
git add src/db/migrations.py
git commit -m "feat(db): add password_reset_tokens table with index"
```

---

## Task 3: Funções de Reset no Repository

**Files:**
- Modificar: `src/db/repository.py`

- [ ] **Step 1: Adicionar funções de reset no final de `src/db/repository.py`**

```python
# ── Reset de senha (apenas admin) ─────────────────────────────────────────────

def criar_reset_token(email: str) -> Optional[str]:
    """
    Cria token de reset de senha para admin com o e-mail informado.
    Retorna o token se o e-mail pertence a um admin ativo, None caso contrário.
    """
    if not _is_postgres():
        return None
    email_norm = (email or "").strip().lower()
    if not email_norm:
        return None

    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT id FROM usuarios_app
                WHERE LOWER(COALESCE(email, '')) = %s
                  AND is_admin = TRUE AND ativo = TRUE
                """,
                (email_norm,),
            )
            row = cur.fetchone()
            if not row:
                return None
            usuario_id = int(row[0])

            # Invalida tokens anteriores do mesmo usuário
            cur.execute(
                "DELETE FROM password_reset_tokens WHERE usuario_id = %s",
                (usuario_id,),
            )

            token = secrets.token_hex(32)
            expira_em = datetime.now() + timedelta(hours=1)
            cur.execute(
                """
                INSERT INTO password_reset_tokens (usuario_id, token, expira_em)
                VALUES (%s, %s, %s)
                """,
                (usuario_id, token, expira_em),
            )
        conn.commit()
        return token
    except Exception:
        return None
    finally:
        conn.close()


def validar_reset_token(token: str) -> Optional[int]:
    """
    Valida token de reset. Retorna usuario_id se válido, None caso contrário.
    Não consome o token — chamar consumir_reset_token após redefinir a senha.
    """
    if not _is_postgres():
        return None
    token = (token or "").strip()
    if not token:
        return None

    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT usuario_id FROM password_reset_tokens
                WHERE token = %s AND usado_em IS NULL AND expira_em > NOW()
                """,
                (token,),
            )
            row = cur.fetchone()
            return int(row[0]) if row else None
    finally:
        conn.close()


def consumir_reset_token(token: str, nova_senha: str) -> bool:
    """
    Atomicamente valida token, redefine senha e marca token como usado.
    Retorna True se sucesso.
    """
    if not _is_postgres():
        return False
    if not nova_senha or len(nova_senha) < 8:
        return False

    conn = get_connection()
    try:
        with conn.cursor() as cur:
            # Atômico: UPDATE só executa se token válido e não expirado
            cur.execute(
                """
                UPDATE password_reset_tokens
                SET usado_em = NOW()
                WHERE token = %s AND usado_em IS NULL AND expira_em > NOW()
                RETURNING usuario_id
                """,
                (token,),
            )
            row = cur.fetchone()
            if not row:
                return False
            usuario_id = int(row[0])

            new_hash = _hash_password(nova_senha)
            cur.execute(
                "UPDATE usuarios_app SET password_hash = %s, salt = %s WHERE id = %s",
                (new_hash, "", usuario_id),
            )
        conn.commit()
        return True
    except Exception:
        return False
    finally:
        conn.close()


def listar_emails_admins() -> list[str]:
    """Retorna lista de e-mails de todos os admins ativos com e-mail cadastrado."""
    if not _is_postgres():
        return []
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT email FROM usuarios_app
                WHERE is_admin = TRUE AND ativo = TRUE
                  AND email IS NOT NULL AND TRIM(email) != ''
                """
            )
            return [row[0].strip() for row in cur.fetchall()]
    except Exception:
        return []
    finally:
        conn.close()
```

- [ ] **Step 2: Verificar importação das funções**

```bash
cd "C:\Users\TI02\Desktop\Planilhas Telefones"
python -c "
from src.db.repository import criar_reset_token, validar_reset_token, consumir_reset_token, listar_emails_admins
print('OK')
"
```
Esperado: `OK`

- [ ] **Step 3: Commit**

```bash
git add src/db/repository.py
git commit -m "feat(auth): add password reset token functions for admin users"
```

---

## Task 4: UI de Reset de Senha no Streamlit

**Files:**
- Modificar: `app.py` (função `_render_login_or_first_user`, linha ~1270)

- [ ] **Step 1: Adicionar imports no topo de `app.py`**

Localizar o bloco de imports `from src.db.repository import (...)` (linha ~47) e adicionar:
```python
        criar_reset_token, validar_reset_token, consumir_reset_token, listar_emails_admins,
```

No bloco de fallback (linha ~58), adicionar:
```python
    criar_reset_token = validar_reset_token = consumir_reset_token = listar_emails_admins = None
```

- [ ] **Step 2: Adicionar função `_render_reset_senha` em `app.py`**

Inserir logo após `_render_login_or_first_user` (após linha ~1329):

```python
def _render_reset_senha() -> None:
    """
    Página de reset de senha para admins.
    Acessada via ?reset_token=<token> na URL ou pelo link na tela de login.
    """
    from src.services.email_service import send_reset_email

    st.markdown(
        """
        <style>
        #MainMenu, header, footer { display: none !important; }
        .block-container { max-width: 440px; margin: 60px auto; }
        </style>
        """,
        unsafe_allow_html=True,
    )

    # ── Passo 2: token na URL → formulário de nova senha ──────────────────────
    params = st.query_params
    token = params.get("reset_token", "")
    if token:
        st.markdown("### Criar nova senha")
        usuario_id = validar_reset_token(token) if validar_reset_token else None
        if not usuario_id:
            st.error("Link inválido ou expirado. Solicite um novo link.")
            if st.button("Voltar ao login"):
                st.query_params.clear()
                st.rerun()
            return

        with st.form("form_nova_senha"):
            nova = st.text_input("Nova senha", type="password", placeholder="mínimo 8 caracteres")
            confirma = st.text_input("Confirmar senha", type="password")
            if st.form_submit_button("Salvar nova senha", use_container_width=True):
                if len(nova) < 8:
                    st.error("Senha deve ter ao menos 8 caracteres.")
                elif nova != confirma:
                    st.error("As senhas não conferem.")
                elif consumir_reset_token and consumir_reset_token(token, nova):
                    st.success("Senha redefinida com sucesso! Faça login.")
                    st.query_params.clear()
                    st.rerun()
                else:
                    st.error("Erro ao redefinir senha. O link pode ter expirado.")
        return

    # ── Passo 1: formulário de e-mail ──────────────────────────────────────────
    st.markdown("### Redefinir senha de administrador")
    st.caption("Insira o e-mail cadastrado da sua conta de administrador.")

    with st.form("form_reset_email"):
        email_input = st.text_input("E-mail do administrador", placeholder="admin@empresa.com.br")
        enviado = st.form_submit_button("Enviar link de redefinição", use_container_width=True)

    if enviado:
        email_input = (email_input or "").strip()
        if not email_input:
            st.warning("Informe o e-mail.")
        elif criar_reset_token:
            token_gerado = criar_reset_token(email_input)
            # Sempre mostrar mesma mensagem — não revelar se e-mail existe
            st.success("Se o e-mail pertence a um administrador ativo, você receberá o link em instantes.")
            if token_gerado:
                app_url = os.environ.get("APP_URL", "http://localhost:8501").rstrip("/")
                reset_url = f"{app_url}/?reset_token={token_gerado}"
                send_reset_email(email_input, reset_url)

    if st.button("← Voltar ao login", use_container_width=False):
        st.session_state["show_reset"] = False
        st.rerun()
```

- [ ] **Step 3: Integrar reset na função `_render_login_or_first_user`**

Localizar em `_render_login_or_first_user` o bloco do formulário de login (após `_render_login_page()`, linha ~1316) e substituir:

**Antes:**
```python
    _render_login_page()
    with st.form("login"):
        u = st.text_input("Usuário", key="login_user", placeholder="seu usuário")
        p = st.text_input("Senha", type="password", key="login_pass", placeholder="••••••••")
        if st.form_submit_button("Entrar", use_container_width=True):
            user = verificar_login(u, p)
            if user:
                st.session_state.authenticated = True
                st.session_state.user = user
                _salvar_sessao_cookie(user)
                st.rerun()
            else:
                st.error("Usuário ou senha incorretos.")
    return False
```

**Depois:**
```python
    # Reset de senha via URL token
    params = st.query_params
    if params.get("reset_token") or st.session_state.get("show_reset"):
        _render_reset_senha()
        return False

    _render_login_page()
    with st.form("login"):
        u = st.text_input("Usuário", key="login_user", placeholder="seu usuário")
        p = st.text_input("Senha", type="password", key="login_pass", placeholder="••••••••")
        if st.form_submit_button("Entrar", use_container_width=True):
            user = verificar_login(u, p)
            if user:
                st.session_state.authenticated = True
                st.session_state.user = user
                _salvar_sessao_cookie(user)
                st.rerun()
            else:
                st.error("Usuário ou senha incorretos.")

    # Link "Esqueci minha senha?" — visível sempre (admin entra com e-mail)
    st.markdown(
        "<div style='text-align:center;margin-top:8px;'>"
        "<small>Esqueceu sua senha de admin? "
        "<a href='#' id='link_reset' style='color:#f2c230;'>Clique aqui</a>"
        "</small></div>",
        unsafe_allow_html=True,
    )
    if st.button("Esqueci minha senha", use_container_width=True, key="btn_reset_senha",
                 help="Apenas administradores podem redefinir senha por e-mail"):
        st.session_state["show_reset"] = True
        st.rerun()

    return False
```

- [ ] **Step 4: Adicionar `APP_URL` no `.env.example`**

```bash
# No .env.example, adicionar na seção de URLs:
# APP_URL=https://gerenciamento.prosperdistribuidora.com.br
APP_URL=http://localhost:8501
```

- [ ] **Step 5: Verificar tela de login abre sem erro**

```bash
streamlit run app.py
```
Esperado: tela de login carrega, botão "Esqueci minha senha" aparece abaixo do form.

- [ ] **Step 6: Commit**

```bash
git add app.py .env.example
git commit -m "feat(auth): admin password reset via email with 1-hour token"
```

---

## Task 5: Notificações de Chamado por E-mail

**Files:**
- Modificar: `src/db/repository.py` (função `criar_chamado`, linha ~983)

- [ ] **Step 1: Adicionar hook de notificação em `criar_chamado`**

Localizar o `return` final da função `criar_chamado` (linha ~1058) e adicionar antes dele:

```python
        # Notifica admins por e-mail (falha silenciosa — não bloqueia criação)
        try:
            from src.services.email_service import send_chamado_notification
            _enviar_notificacao_chamado(
                numero_chamado=str(row[1]),
                titulo=str(row[6]),
                solicitante_id=str(solicitante_val or ""),
                aberto_em=str(row[8]),
                descricao=str(row[7] or ""),
            )
        except Exception:
            pass
```

- [ ] **Step 2: Adicionar função helper `_enviar_notificacao_chamado`**

Inserir logo antes de `criar_chamado` (linha ~983):

```python
def _enviar_notificacao_chamado(
    numero_chamado: str,
    titulo: str,
    solicitante_id: str,
    aberto_em: str,
    descricao: str = "",
) -> None:
    """Envia e-mail para todos os admins quando chamado é criado. Falha silenciosa."""
    try:
        from src.services.email_service import send_chamado_notification

        admins = listar_emails_admins()
        if not admins:
            return

        # Buscar nome do solicitante
        solicitante = "Usuário"
        if solicitante_id and solicitante_id.isdigit():
            conn = get_connection()
            try:
                with conn.cursor() as cur:
                    cur.execute(
                        "SELECT username FROM usuarios_app WHERE id = %s",
                        (int(solicitante_id),),
                    )
                    row = cur.fetchone()
                    if row:
                        solicitante = str(row[0])
            finally:
                conn.close()

        aberto_fmt = str(aberto_em)[:19].replace("T", " ") if aberto_em else ""

        send_chamado_notification(
            admins_emails=admins,
            numero_chamado=numero_chamado,
            titulo=titulo,
            solicitante=solicitante,
            aberto_em=aberto_fmt,
            descricao=descricao,
        )
    except Exception:
        pass
```

- [ ] **Step 3: Verificar importação**

```bash
cd "C:\Users\TI02\Desktop\Planilhas Telefones"
python -c "from src.db.repository import criar_chamado; print('OK')"
```
Esperado: `OK`

- [ ] **Step 4: Commit**

```bash
git add src/db/repository.py
git commit -m "feat(chamados): notify all admin emails when new ticket is created"
```

---

## Task 6: Variáveis SMTP no .env.example

**Files:**
- Modificar: `.env.example`

- [ ] **Step 1: Adicionar bloco SMTP no `.env.example`**

Adicionar após a seção `--- URLs de integração ---`:

```bash
# --- E-mail SMTP (reset de senha + notificações de chamado) ---
# Locaweb: host e porta padrão já configurados abaixo
SMTP_HOST=email.locaweb.com.br
SMTP_PORT=587
SMTP_USER=suporte@prosperdistribuidora.com.br
SMTP_PASSWORD=SUA_SENHA_EMAIL_AQUI
SMTP_FROM=suporte@prosperdistribuidora.com.br

# URL pública do app Streamlit (usada nos links de reset de senha)
# Em produção: substitua pelo domínio real
APP_URL=http://localhost:8501
```

- [ ] **Step 2: Commit**

```bash
git add .env.example
git commit -m "docs: add SMTP and APP_URL variables to .env.example"
```

---

## Task 7: Fixes de Produção — Exception Leakage

**Files:**
- Modificar: `Sistema de Chamados TI/backend/app/api/v1/endpoints/telefones.py`
- Modificar: `Sistema de Chamados TI/backend/app/api/v1/endpoints/auth.py`

- [ ] **Step 1: Corrigir `telefones.py` — substituir 4 blocos de exception leakage**

Em `telefones.py`, substituir cada bloco `except Exception as exc:` que usa `f"Erro ao ...: {type(exc).__name__}: {exc}"`:

**buscar_linha (linha ~84):**
```python
    except Exception as exc:
        logger.error("buscar_linha error: %s", exc, exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Erro interno ao buscar linha.",
        )
```

**liberar_linha (linha ~110):**
```python
    except Exception as exc:
        logger.error("liberar_linha error: %s", exc, exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Erro interno ao liberar linha.",
        )
```

**atribuir_linha (linha ~135):**
```python
    except Exception as exc:
        logger.error("atribuir_linha error: %s", exc, exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Erro interno ao atribuir linha.",
        )
```

**atualizar_aparelho (linha ~162):**
```python
    except Exception as exc:
        logger.error("atualizar_aparelho error: %s", exc, exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Erro interno ao atualizar aparelho.",
        )
```

**transferir (linha ~188):**
```python
    except Exception as exc:
        logger.error("transferir error: %s", exc, exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Erro interno ao transferir linha.",
        )
```

Adicionar no topo do arquivo (após imports):
```python
import logging
logger = logging.getLogger(__name__)
```

- [ ] **Step 2: Corrigir `auth.py` — exception leakage (linha ~178)**

```python
        except Exception as exc:
            logger.error("sso_exchange error: %s", exc, exc_info=True)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Erro interno ao processar autenticação.",
            )
```

Adicionar no topo do `auth.py`:
```python
import logging
logger = logging.getLogger(__name__)
```

- [ ] **Step 3: Verificar sintaxe**

```bash
cd "C:\Users\TI02\Desktop\Planilhas Telefones"
python -m py_compile "Sistema de Chamados TI/backend/app/api/v1/endpoints/telefones.py" && echo "OK telefones"
python -m py_compile "Sistema de Chamados TI/backend/app/api/v1/endpoints/auth.py" && echo "OK auth"
```
Esperado: `OK telefones` e `OK auth`

- [ ] **Step 4: Commit**

```bash
git add "Sistema de Chamados TI/backend/app/api/v1/endpoints/telefones.py"
git add "Sistema de Chamados TI/backend/app/api/v1/endpoints/auth.py"
git commit -m "fix(security): replace exception detail leakage with generic messages in production"
```

---

## Task 8: Fix JWT_SECRET Obrigatório

**Files:**
- Modificar: `Sistema de Chamados TI/backend/app/api/deps.py` (linha 25)
- Modificar: `Sistema de Chamados TI/backend/app/api/v1/endpoints/auth.py` (linha 43)

- [ ] **Step 1: Corrigir `deps.py` — remover fallback para COOKIES_PASSWORD**

**Antes (linha 25):**
```python
    secret = (os.environ.get("JWT_SECRET") or os.environ.get("COOKIES_PASSWORD", "")).strip()
```

**Depois:**
```python
    secret = os.environ.get("JWT_SECRET", "").strip()
```

- [ ] **Step 2: Corrigir `auth.py` — remover fallback para COOKIES_PASSWORD**

**Antes (linha 43):**
```python
    secret = os.environ.get("JWT_SECRET") or os.environ.get("COOKIES_PASSWORD")
    if not secret:
        raise RuntimeError("JWT_SECRET nao configurado e COOKIES_PASSWORD nao existe.")
```

**Depois:**
```python
    secret = os.environ.get("JWT_SECRET", "").strip()
    if not secret:
        raise RuntimeError("JWT_SECRET nao configurado no ambiente.")
```

- [ ] **Step 3: Verificar sintaxe**

```bash
python -m py_compile "Sistema de Chamados TI/backend/app/api/deps.py" && echo "OK deps"
python -m py_compile "Sistema de Chamados TI/backend/app/api/v1/endpoints/auth.py" && echo "OK auth"
```
Esperado: ambos `OK`

- [ ] **Step 4: Commit**

```bash
git add "Sistema de Chamados TI/backend/app/api/deps.py"
git add "Sistema de Chamados TI/backend/app/api/v1/endpoints/auth.py"
git commit -m "fix(security): make JWT_SECRET mandatory, remove COOKIES_PASSWORD fallback"
```

---

## Task 9: Fix sso_codes — Limpeza Global

**Files:**
- Modificar: `src/db/repository.py` (função `criar_sso_code`, linha ~393)

- [ ] **Step 1: Substituir limpeza parcial por global**

Localizar em `criar_sso_code`:

**Antes:**
```python
            cur.execute(
                "DELETE FROM sso_codes WHERE usuario_id = %s AND expira_em < NOW()",
                (usuario_app_id_int,),
            )
```

**Depois:**
```python
            # Limpa todos os codes expirados (não só do usuário atual)
            cur.execute("DELETE FROM sso_codes WHERE expira_em < NOW()")
```

- [ ] **Step 2: Converter recursão em loop**

Localizar o bloco `except UniqueViolation` em `criar_sso_code`:

**Antes:**
```python
    except UniqueViolation:
        return criar_sso_code(usuario_app_id_int, expira_em, db_path=db_path)
```

**Depois:**
```python
    except UniqueViolation:
        # Colisão improvável com token_hex(32) — loop máx 3 tentativas
        for _ in range(3):
            new_code = secrets.token_hex(32)
            try:
                conn2 = get_connection(db_path)
                with conn2.cursor() as c2:
                    c2.execute(
                        "INSERT INTO sso_codes (code, usuario_id, expira_em, usado_em) VALUES (%s,%s,%s,NULL)",
                        (new_code, usuario_app_id_int, expira_em),
                    )
                conn2.commit()
                conn2.close()
                return new_code
            except UniqueViolation:
                continue
            except Exception:
                break
        return None
```

- [ ] **Step 3: Verificar sintaxe**

```bash
python -m py_compile src/db/repository.py && echo "OK"
```
Esperado: `OK`

- [ ] **Step 4: Commit**

```bash
git add src/db/repository.py
git commit -m "fix(security): global sso_codes cleanup and bounded retry loop"
```

---

## Task 10: Senha Mínima 8 Chars + Arquivar Migration Script

**Files:**
- Modificar: `src/pages/config_admin.py` (linha 335)
- Modificar: `app.py` (linha ~1298 e ~1309)
- Modificar: `src/db/repository.py` (função `atualizar_senha_usuario`, linha ~274)
- Mover: `scripts/migrate_sqlite_to_postgres.py` → `scripts/archive/migrate_sqlite_to_postgres.py`

- [ ] **Step 1: Corrigir senha mínima em `config_admin.py` (linha 335)**

**Antes:**
```python
        elif len(np1) < 4:
            st.error("Senha deve ter ao menos 4 caracteres.")
```

**Depois:**
```python
        elif len(np1) < 8:
            st.error("Senha deve ter ao menos 8 caracteres.")
```

- [ ] **Step 2: Corrigir senha mínima em `app.py` (linha ~1298 e ~1309)**

**Antes (primeiro usuário):**
```python
                if u.strip() and len(p) >= 4:
```
**Depois:**
```python
                if u.strip() and len(p) >= 8:
```

**Antes (mensagem de erro):**
```python
                    st.error("Usuário e senha (mín. 4 caracteres) obrigatórios.")
```
**Depois:**
```python
                    st.error("Usuário e senha (mín. 8 caracteres) obrigatórios.")
```

- [ ] **Step 3: Corrigir `atualizar_senha_usuario` em `repository.py` (linha ~274)**

**Antes:**
```python
    if not user or len(nova_senha or "") < 4:
```
**Depois:**
```python
    if not user or len(nova_senha or "") < 8:
```

- [ ] **Step 4: Arquivar script de migração**

```bash
cd "C:\Users\TI02\Desktop\Planilhas Telefones"
mkdir -p scripts/archive
git mv scripts/migrate_sqlite_to_postgres.py scripts/archive/migrate_sqlite_to_postgres.py
```

- [ ] **Step 5: Verificar sintaxe dos arquivos modificados**

```bash
python -m py_compile src/pages/config_admin.py && echo "OK config_admin"
python -m py_compile app.py && echo "OK app"
python -m py_compile src/db/repository.py && echo "OK repository"
```
Esperado: todos `OK`

- [ ] **Step 6: Commit**

```bash
git add src/pages/config_admin.py app.py src/db/repository.py scripts/archive/migrate_sqlite_to_postgres.py
git commit -m "fix(security): raise min password to 8 chars, archive migration script"
```

---

## Task 11: Verificação Final de Produção

- [ ] **Step 1: Rodar security check**

```bash
cd "C:\Users\TI02\Desktop\Planilhas Telefones"
node .claude/skills/security-check/scripts/check.js
```
Esperado: nota ≥ 95/100

- [ ] **Step 2: Verificar app inicia**

```bash
streamlit run app.py
```
Checklist:
- [ ] Tela de login carrega sem erro
- [ ] Botão "Esqueci minha senha" aparece
- [ ] Formulário de e-mail abre ao clicar
- [ ] App principal carrega após login

- [ ] **Step 3: Verificar variáveis obrigatórias no `.env`**

```bash
grep -E "^(DATABASE_URL|COOKIES_PASSWORD|JWT_SECRET|SMTP_USER|SMTP_PASSWORD|APP_URL)" .env
```
Esperado: todas 6 variáveis presentes e preenchidas.

- [ ] **Step 4: Commit final**

```bash
git add -A
git commit -m "chore: production readiness — email notifications, password reset, security fixes"
```

---

## Resumo das Entregas

| # | Feature | Arquivo(s) |
|---|---------|-----------|
| 1 | Serviço SMTP compartilhado | `src/services/email_service.py` |
| 2 | Tabela `password_reset_tokens` | `src/db/migrations.py` |
| 3 | Funções reset no repository | `src/db/repository.py` |
| 4 | UI reset senha (Streamlit) | `app.py` |
| 5 | Notificação chamado aberto | `src/db/repository.py` |
| 6 | Variáveis SMTP no .env.example | `.env.example` |
| 7 | Fix exception leakage | `telefones.py`, `auth.py` |
| 8 | Fix JWT_SECRET obrigatório | `deps.py`, `auth.py` |
| 9 | Fix sso_codes cleanup + loop | `src/db/repository.py` |
| 10 | Senha mín. 8 chars + arquivar script | `config_admin.py`, `app.py`, `repository.py` |
| 11 | Verificação final | — |
