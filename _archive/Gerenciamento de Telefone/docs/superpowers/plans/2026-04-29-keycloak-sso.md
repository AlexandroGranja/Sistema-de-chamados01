# Keycloak SSO Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended)
> or superpowers:executing-plans. Steps use checkbox (`- [ ]`) syntax.

**Goal:** Substituir os dois sistemas de login independentes (Streamlit + FastAPI) por Keycloak OIDC, fornecendo single sign-on com segurança corporativa para os ~30 usuários da empresa.

**Architecture:** Keycloak self-hosted (Docker) no servidor da empresa atua como único provedor de identidade (IdP). Streamlit autentica via OIDC usando `streamlit-keycloak`. FastAPI valida tokens RS256 emitidos pelo Keycloak via endpoint JWKS. A bridge `sso_code` entre Streamlit e React é removida — o cookie de sessão do Keycloak entrega SSO transparente. Usuários do PostgreSQL são migrados para Keycloak via script usando Admin REST API.

**Tech Stack:** Keycloak 24+ (Docker Compose), PostgreSQL 16 (banco separado para Keycloak), streamlit-keycloak, python-jose[cryptography], httpx, keycloak-js + @react-keycloak/web (para quando o frontend React for criado)

---

## Pré-requisitos

- Docker e Docker Compose instalados no servidor
- Servidor acessível em IP fixo (ex: `192.168.1.100`) ou domínio
- Porta 8080 disponível para Keycloak
- Python 3.10+ e Node.js 18+ instalados

---

## Task 1: Keycloak Docker Setup

**Files:**
- Create: `keycloak/docker-compose.yml`
- Create: `keycloak/.env.keycloak`
- Create: `keycloak/README.md`

- [ ] **Step 1: Criar diretório keycloak e arquivo .env**

```bash
mkdir -p keycloak
```

Criar `keycloak/.env.keycloak` com as variáveis (substituir senhas reais):
```env
KEYCLOAK_DB_PASSWORD=KC_DB_SENHA_FORTE_AQUI
KEYCLOAK_ADMIN_PASSWORD=KC_ADMIN_SENHA_FORTE_AQUI
KEYCLOAK_HOSTNAME=192.168.1.100
```

- [ ] **Step 2: Criar docker-compose.yml**

Criar `keycloak/docker-compose.yml`:
```yaml
version: '3.8'

services:
  keycloak-db:
    image: postgres:16
    container_name: keycloak-db
    environment:
      POSTGRES_DB: keycloak
      POSTGRES_USER: keycloak
      POSTGRES_PASSWORD: ${KEYCLOAK_DB_PASSWORD}
    volumes:
      - keycloak_db_data:/var/lib/postgresql/data
    restart: unless-stopped
    networks:
      - keycloak-net

  keycloak:
    image: quay.io/keycloak/keycloak:24.0
    container_name: keycloak
    command: start-dev
    environment:
      KC_DB: postgres
      KC_DB_URL: jdbc:postgresql://keycloak-db:5432/keycloak
      KC_DB_USERNAME: keycloak
      KC_DB_PASSWORD: ${KEYCLOAK_DB_PASSWORD}
      KEYCLOAK_ADMIN: admin
      KEYCLOAK_ADMIN_PASSWORD: ${KEYCLOAK_ADMIN_PASSWORD}
      KC_HTTP_PORT: 8080
      KC_HOSTNAME: ${KEYCLOAK_HOSTNAME}
      KC_HOSTNAME_STRICT: false
      KC_HOSTNAME_STRICT_HTTPS: false
    ports:
      - "8080:8080"
    depends_on:
      - keycloak-db
    restart: unless-stopped
    networks:
      - keycloak-net

volumes:
  keycloak_db_data:

networks:
  keycloak-net:
    driver: bridge
```

- [ ] **Step 3: Iniciar Keycloak**

```bash
cd keycloak
docker compose --env-file .env.keycloak up -d
```

- [ ] **Step 4: Verificar Keycloak acessível**

Aguardar ~60 segundos e acessar:
```
http://192.168.1.100:8080/admin
```
Login: `admin` / senha do `KEYCLOAK_ADMIN_PASSWORD`

Esperado: painel admin do Keycloak carrega.

- [ ] **Step 5: Commit**

```bash
git add keycloak/docker-compose.yml keycloak/README.md
git commit -m "infra: add Keycloak Docker Compose setup"
```

---

## Task 2: Keycloak Realm e Clients

**Objetivo:** Criar o realm `prosper`, dois clients (Streamlit e React), e roles `admin`/`user`.

> Executar via Admin Console (http://192.168.1.100:8080/admin) OU via script de automação abaixo.

- [ ] **Step 1: Criar Realm**

No Admin Console:
- Clicar em "Create realm"
- Name: `prosper`
- Display name: `Prosper Distribuidora`
- Enabled: ON
- Clicar "Create"

- [ ] **Step 2: Criar Client para Streamlit**

Em Realm `prosper` → Clients → Create client:

| Campo | Valor |
|-------|-------|
| Client type | OpenID Connect |
| Client ID | `streamlit-app` |
| Name | Gerenciamento de Telefones |
| Client authentication | ON (Confidential) |
| Authentication flow | Standard flow (Authorization Code) |
| Valid redirect URIs | `http://localhost:8501/*` e `http://IP_SERVIDOR:8501/*` |
| Web origins | `http://localhost:8501` e `http://IP_SERVIDOR:8501` |

Após criar → aba "Credentials" → copiar o **Client Secret**.

- [ ] **Step 3: Criar Client para React (quando frontend for criado)**

Em Realm `prosper` → Clients → Create client:

| Campo | Valor |
|-------|-------|
| Client type | OpenID Connect |
| Client ID | `chamados-react` |
| Client authentication | OFF (Public) |
| Authentication flow | Standard flow |
| Valid redirect URIs | `http://localhost:3000/*` e `http://IP_SERVIDOR:3000/*` |
| Web origins | `http://localhost:3000` e `http://IP_SERVIDOR:3000` |

- [ ] **Step 4: Criar Roles no Realm**

Realm Settings → Roles → Create role:
1. Nome: `admin` — Descrição: Acesso administrativo total
2. Nome: `user` — Descrição: Acesso padrão de usuário

- [ ] **Step 5: Configurar Token com roles no claim**

Client `streamlit-app` → Client scopes → Add mapper → By configuration → User Realm Role:
- Name: `realm_roles`
- Token Claim Name: `realm_access.roles`
- Add to access token: ON

- [ ] **Step 6: Anotar dados do Keycloak**

```
KEYCLOAK_URL=http://192.168.1.100:8080
KEYCLOAK_REALM=prosper
KEYCLOAK_CLIENT_ID_STREAMLIT=streamlit-app
KEYCLOAK_CLIENT_SECRET_STREAMLIT=<secret copiado no Step 2>
KEYCLOAK_CLIENT_ID_REACT=chamados-react
```

---

## Task 3: Script de Migração de Usuários

**Files:**
- Create: `scripts/migrate_users_to_keycloak.py`

**Objetivo:** Ler usuários do PostgreSQL e criar no Keycloak via Admin REST API. Usuários receberão e-mail para definir nova senha.

- [ ] **Step 1: Instalar dependência temporária**

```bash
pip install httpx
```

- [ ] **Step 2: Criar script de migração**

Criar `scripts/migrate_users_to_keycloak.py`:

```python
"""
Migra usuários de usuarios_app (PostgreSQL) para Keycloak.
Executa UMA VEZ. Usuários recebem email para redefinir senha.

Uso:
  python scripts/migrate_users_to_keycloak.py
"""
import os
import sys
import httpx
from dotenv import load_dotenv

load_dotenv()

KEYCLOAK_URL = os.environ["KEYCLOAK_URL"]          # ex: http://192.168.1.100:8080
KEYCLOAK_REALM = os.environ["KEYCLOAK_REALM"]      # prosper
KEYCLOAK_ADMIN_USER = os.environ["KEYCLOAK_ADMIN_USER"]    # admin
KEYCLOAK_ADMIN_PASS = os.environ["KEYCLOAK_ADMIN_PASSWORD"]
DATABASE_URL = os.environ["DATABASE_URL"]

import psycopg


def get_admin_token(client: httpx.Client) -> str:
    resp = client.post(
        f"{KEYCLOAK_URL}/realms/master/protocol/openid-connect/token",
        data={
            "grant_type": "password",
            "client_id": "admin-cli",
            "username": KEYCLOAK_ADMIN_USER,
            "password": KEYCLOAK_ADMIN_PASS,
        },
    )
    resp.raise_for_status()
    return resp.json()["access_token"]


def list_pg_users() -> list[dict]:
    with psycopg.connect(DATABASE_URL) as conn:
        rows = conn.execute(
            "SELECT username, email, nome_exibicao, is_admin, ativo FROM usuarios_app ORDER BY id"
        ).fetchall()
    return [
        {
            "username": r[0],
            "email": r[1] or "",
            "nome_exibicao": r[2] or r[0],
            "is_admin": r[3],
            "ativo": r[4],
        }
        for r in rows
    ]


def create_keycloak_user(client: httpx.Client, token: str, user: dict) -> str | None:
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    payload = {
        "username": user["username"],
        "email": user["email"] or f"{user['username']}@prosper.local",
        "firstName": user["nome_exibicao"].split()[0] if user["nome_exibicao"] else user["username"],
        "lastName": " ".join(user["nome_exibicao"].split()[1:]) if len(user["nome_exibicao"].split()) > 1 else "",
        "enabled": user["ativo"],
        "emailVerified": True,
        "realmRoles": ["admin"] if user["is_admin"] else ["user"],
    }
    resp = client.post(
        f"{KEYCLOAK_URL}/admin/realms/{KEYCLOAK_REALM}/users",
        json=payload,
        headers=headers,
    )
    if resp.status_code == 409:
        print(f"  SKIP {user['username']} (já existe)")
        return None
    resp.raise_for_status()
    location = resp.headers.get("Location", "")
    user_id = location.rstrip("/").split("/")[-1]
    return user_id


def assign_realm_role(client: httpx.Client, token: str, user_id: str, role_name: str) -> None:
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    roles_resp = client.get(
        f"{KEYCLOAK_URL}/admin/realms/{KEYCLOAK_REALM}/roles",
        headers=headers,
    )
    roles_resp.raise_for_status()
    role = next((r for r in roles_resp.json() if r["name"] == role_name), None)
    if not role:
        print(f"  WARN role '{role_name}' não encontrada")
        return
    client.post(
        f"{KEYCLOAK_URL}/admin/realms/{KEYCLOAK_REALM}/users/{user_id}/role-mappings/realm",
        json=[{"id": role["id"], "name": role["name"]}],
        headers=headers,
    )


def send_password_reset(client: httpx.Client, token: str, user_id: str) -> None:
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    client.put(
        f"{KEYCLOAK_URL}/admin/realms/{KEYCLOAK_REALM}/users/{user_id}/execute-actions-email",
        json=["UPDATE_PASSWORD"],
        headers=headers,
    )


def main():
    users = list_pg_users()
    print(f"Encontrados {len(users)} usuários no PostgreSQL.")

    with httpx.Client(timeout=30) as client:
        token = get_admin_token(client)

        for user in users:
            print(f"Migrando: {user['username']} (admin={user['is_admin']}) ...")
            user_id = create_keycloak_user(client, token, user)
            if user_id:
                role = "admin" if user["is_admin"] else "user"
                assign_realm_role(client, token, user_id, role)
                if user["email"]:
                    send_password_reset(client, token, user_id)
                    print(f"  OK — email de reset enviado para {user['email']}")
                else:
                    print(f"  OK — sem email, definir senha manualmente no Admin Console")

    print("\nMigração concluída.")


if __name__ == "__main__":
    main()
```

- [ ] **Step 3: Executar migração**

```bash
KEYCLOAK_ADMIN_USER=admin python scripts/migrate_users_to_keycloak.py
```

Esperado: lista de usuários migrados, emails de reset enviados.

- [ ] **Step 4: Verificar no Admin Console**

Keycloak Admin → Realm `prosper` → Users → verificar todos os usuários aparecem com roles corretas.

- [ ] **Step 5: Commit**

```bash
git add scripts/migrate_users_to_keycloak.py
git commit -m "feat: add user migration script PostgreSQL → Keycloak"
```

---

## Task 4: FastAPI — Substituir Validação JWT por Keycloak JWKS

**Files:**
- Modify: `Sistema de Chamados TI/backend/app/api/deps.py:1-89`
- Modify: `Sistema de Chamados TI/backend/app/api/v1/endpoints/auth.py`
- Modify: `Sistema de Chamados TI/backend/app/main.py`
- Modify: `Sistema de Chamados TI/backend/requirements.txt` (se existir)

**Objetivo:** FastAPI para de usar o `JWT_SECRET` HS256 próprio e passa a validar tokens RS256 emitidos pelo Keycloak via JWKS público.

- [ ] **Step 1: Instalar dependências**

Verificar se existe `requirements.txt` em `Sistema de Chamados TI/backend/`:
```bash
cat "Sistema de Chamados TI/backend/requirements.txt"
```

Adicionar ao arquivo:
```
python-jose[cryptography]>=3.3.0
httpx>=0.27.0
```

Instalar:
```bash
cd "Sistema de Chamados TI/backend"
pip install "python-jose[cryptography]" "httpx>=0.27.0"
```

- [ ] **Step 2: Reescrever deps.py**

Substituir conteúdo completo de `Sistema de Chamados TI/backend/app/api/deps.py`:

```python
import os
import time
from typing import Any, Dict

import httpx
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt

_bearer = HTTPBearer()

KEYCLOAK_URL = os.environ["KEYCLOAK_URL"]
KEYCLOAK_REALM = os.environ["KEYCLOAK_REALM"]
_JWKS_URL = f"{KEYCLOAK_URL}/realms/{KEYCLOAK_REALM}/protocol/openid-connect/certs"

_jwks_cache: Dict | None = None
_jwks_cache_at: float = 0.0
_JWKS_TTL = 3600  # 1h


def _get_jwks() -> Dict:
    global _jwks_cache, _jwks_cache_at
    if _jwks_cache and (time.time() - _jwks_cache_at) < _JWKS_TTL:
        return _jwks_cache
    resp = httpx.get(_JWKS_URL, timeout=10)
    resp.raise_for_status()
    _jwks_cache = resp.json()
    _jwks_cache_at = time.time()
    return _jwks_cache


def verify_token(
    credentials: HTTPAuthorizationCredentials = Depends(_bearer),
) -> Dict[str, Any]:
    token = credentials.credentials
    try:
        unverified_header = jwt.get_unverified_header(token)
    except JWTError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token malformado")

    jwks = _get_jwks()
    kid = unverified_header.get("kid")
    key = next((k for k in jwks.get("keys", []) if k.get("kid") == kid), None)
    if not key:
        _jwks_cache = None  # Forçar refresh (rotação de chave)
        jwks = _get_jwks()
        key = next((k for k in jwks.get("keys", []) if k.get("kid") == kid), None)
        if not key:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Chave JWT não encontrada")

    try:
        payload = jwt.decode(
            token,
            key,
            algorithms=["RS256"],
            options={"verify_aud": False},
        )
    except JWTError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Token inválido: {exc}",
        )

    return payload
```

- [ ] **Step 3: Verificar que payload do Keycloak tem campos necessários**

O token Keycloak contém:
```json
{
  "sub": "uuid-do-usuario",
  "preferred_username": "alexandro",
  "realm_access": { "roles": ["admin"] },
  "email": "...",
  "exp": 1234567890
}
```

Atualizar qualquer uso de `payload["username"]` para `payload.get("preferred_username")` e `payload["is_admin"]` para `"admin" in payload.get("realm_access", {}).get("roles", [])` nos endpoints.

Buscar todos os usos:
```bash
grep -rn "payload\[" "Sistema de Chamados TI/backend/app/api/"
```

- [ ] **Step 4: Remover endpoint SSO exchange (não mais necessário)**

Em `Sistema de Chamados TI/backend/app/api/v1/endpoints/auth.py`, remover ou comentar:
- O endpoint `POST /sso-exchange`
- Models `SSOExchangeRequest` e `SSOExchangeResponse`
- Imports relativos a JWT HS256 (base64, hashlib, hmac, secrets para tokens)

Manter: qualquer endpoint de dados de usuário que ainda seja usado.

Se o arquivo ficar vazio de rotas úteis, remover o router dele em `main.py`.

- [ ] **Step 5: Atualizar variáveis de ambiente no FastAPI**

Remover do `.env`: `JWT_SECRET`, `JWT_ACCESS_EXPIRES_SECONDS`, `JWT_REFRESH_EXPIRES_SECONDS`

Adicionar ao `.env`:
```env
KEYCLOAK_URL=http://192.168.1.100:8080
KEYCLOAK_REALM=prosper
```

- [ ] **Step 6: Testar endpoint protegido**

Obter token de teste no Keycloak:
```bash
curl -X POST http://192.168.1.100:8080/realms/prosper/protocol/openid-connect/token \
  -d "grant_type=password&client_id=streamlit-app&client_secret=SECRET&username=alexandro&password=SENHA" \
  | python -m json.tool
```

Usar o `access_token` retornado:
```bash
curl -H "Authorization: Bearer ACCESS_TOKEN" http://localhost:8000/api/telefones/
```

Esperado: resposta válida (não 401).

- [ ] **Step 7: Commit**

```bash
git add "Sistema de Chamados TI/backend/"
git commit -m "feat(api): replace custom JWT with Keycloak RS256 JWKS validation"
```

---

## Task 5: Streamlit — Substituir Login por OIDC Keycloak

**Files:**
- Modify: `app.py` (linhas 18-40, 994-1023, 1267-1412, 1672-1682)
- Modify: `requirements.txt`
- Modify: `src/db/repository.py` (remover funções de auth local)
- Modify: `.env`

**Objetivo:** Streamlit usa `streamlit-keycloak` para login OIDC. Remove cookies próprios, verificação de senha, SSO bridge.

- [ ] **Step 1: Instalar streamlit-keycloak**

```bash
pip install streamlit-keycloak
```

Adicionar ao `requirements.txt`:
```
streamlit-keycloak>=0.4.0
```

Remover de `requirements.txt`:
```
streamlit-cookies-manager-v2    # remover esta linha
```

- [ ] **Step 2: Reescrever inicialização de auth em app.py (linhas 18-40)**

Substituir bloco `_init_cookies()` e variáveis `HAS_COOKIES`/`_cookies` por:

```python
import os as _os

_KEYCLOAK_URL = _os.environ.get("KEYCLOAK_URL", "")
_KEYCLOAK_REALM = _os.environ.get("KEYCLOAK_REALM", "prosper")
_KEYCLOAK_CLIENT_ID = _os.environ.get("KEYCLOAK_CLIENT_ID_STREAMLIT", "streamlit-app")
```

- [ ] **Step 3: Substituir função _render_login_or_first_user (linhas 1272-1344)**

A nova função usa `streamlit_keycloak.login()` que retorna um objeto com `.authenticated`, `.access_token`, `.user_info`.

Substituir pelo seguinte bloco no início do `main()` ou no ponto onde o auth é verificado:

```python
from streamlit_keycloak import login as _kc_login

def _autenticar_keycloak() -> bool:
    """
    Inicia OIDC flow via Keycloak. Retorna True se autenticado.
    Popula st.session_state.user e st.session_state.authenticated.
    """
    auth = _kc_login(
        url=_KEYCLOAK_URL,
        realm=_KEYCLOAK_REALM,
        client_id=_KEYCLOAK_CLIENT_ID,
    )

    if not auth.authenticated:
        return False

    username = auth.user_info.get("preferred_username", "")
    roles = auth.user_info.get("realm_access", {}).get("roles", [])
    is_admin = "admin" in roles

    st.session_state.authenticated = True
    st.session_state.user = {"username": username, "is_admin": is_admin}
    st.session_state.access_token = auth.access_token

    _garantir_usuario_local(username, is_admin)
    return True


def _garantir_usuario_local(username: str, is_admin: bool) -> None:
    """Upsert do usuário no PostgreSQL para manter FKs de auditoria."""
    if not HAS_DB:
        return
    try:
        with _get_pg_conn() as conn:
            conn.execute(
                """
                INSERT INTO usuarios_app (username, is_admin, auth_provider, ativo)
                VALUES (%s, %s, 'keycloak', TRUE)
                ON CONFLICT (username) DO UPDATE
                  SET is_admin = EXCLUDED.is_admin,
                      auth_provider = 'keycloak',
                      atualizado_em = NOW()
                """,
                (username, is_admin),
            )
    except Exception:
        pass
```

Substituir chamada `_render_login_or_first_user()` por `_autenticar_keycloak()` no fluxo principal.

- [ ] **Step 4: Remover imports de auth local em app.py**

Remover das importações de `src.db.repository`:
```python
# REMOVER estas linhas:
verificar_login,
criar_usuario,     # manter se ainda usado em user management
criar_sessao,
validar_sessao,
encerrar_sessao,
obter_usuario_app_id,
criar_sso_code,
criar_reset_token,
validar_reset_token,
consumir_reset_token,
listar_emails_admins,
```

Remover import de:
```python
from streamlit_cookies_manager import EncryptedCookieManager  # remover
from src.services.email_service import send_reset_email       # remover se só usado no reset
```

- [ ] **Step 5: Substituir logout (linhas 1672-1682)**

O logout do Keycloak é feito via redirect para o endpoint de logout do Keycloak. Substituir o bloco de logout:

```python
if nav["logout_clicked"]:
    st.session_state.authenticated = False
    st.session_state.user = None
    st.session_state.pop("access_token", None)
    # Keycloak cuida da invalidação da sessão OIDC automaticamente
    # streamlit-keycloak faz o redirect de logout
    st.rerun()
```

- [ ] **Step 6: Remover SSO bridge (sso_code) de app.py**

Buscar e remover o bloco que gera `sso_code`:
```bash
grep -n "criar_sso_code\|sso_code_cache\|sso_code" app.py
```

Substituir o botão "Chamados" por link direto para a URL do sistema de chamados (sem SSO code — Keycloak provê SSO via cookie próprio):

```python
chamados_url = get_chamados_app_url()
if chamados_url:
    st.sidebar.link_button("Sistema de Chamados", chamados_url)
```

- [ ] **Step 7: Atualizar .env**

Adicionar ao `.env`:
```env
KEYCLOAK_URL=http://192.168.1.100:8080
KEYCLOAK_REALM=prosper
KEYCLOAK_CLIENT_ID_STREAMLIT=streamlit-app
KEYCLOAK_CLIENT_SECRET_STREAMLIT=<secret do Admin Console>
```

Remover do `.env`:
```env
# COOKIES_PASSWORD=...   (remover)
# JWT_SECRET=...         (remover — manter só se FastAPI ainda usa)
```

- [ ] **Step 8: Testar login Streamlit**

```bash
streamlit run app.py
```

Acessar `http://localhost:8501`. Esperado:
1. Streamlit abre e exibe botão/redirect para Keycloak
2. Login na tela do Keycloak funciona
3. Retorna ao Streamlit autenticado com nome de usuário correto
4. `st.session_state.user["is_admin"]` correto para usuário admin

- [ ] **Step 9: Commit**

```bash
git add app.py requirements.txt
git commit -m "feat(streamlit): replace cookie auth with Keycloak OIDC via streamlit-keycloak"
```

---

## Task 6: React Frontend — OIDC com Keycloak (quando frontend for criado)

> **Nota:** O frontend React ainda não existe no repositório. Esta task é um template para quando o frontend React do Sistema de Chamados for criado.

**Files:**
- Create: `Sistema de Chamados TI/frontend/src/keycloak.js`
- Modify: `Sistema de Chamados TI/frontend/src/main.jsx`
- Modify: `Sistema de Chamados TI/frontend/.env`

- [ ] **Step 1: Instalar dependências React**

```bash
cd "Sistema de Chamados TI/frontend"
npm install keycloak-js @react-keycloak/web
```

- [ ] **Step 2: Criar keycloak.js**

Criar `src/keycloak.js`:
```javascript
import Keycloak from 'keycloak-js';

const keycloak = new Keycloak({
  url: import.meta.env.VITE_KEYCLOAK_URL,
  realm: import.meta.env.VITE_KEYCLOAK_REALM,
  clientId: import.meta.env.VITE_KEYCLOAK_CLIENT_ID,
});

export default keycloak;
```

- [ ] **Step 3: Criar .env do frontend**

Criar `Sistema de Chamados TI/frontend/.env`:
```env
VITE_KEYCLOAK_URL=http://192.168.1.100:8080
VITE_KEYCLOAK_REALM=prosper
VITE_KEYCLOAK_CLIENT_ID=chamados-react
```

- [ ] **Step 4: Envolver App com ReactKeycloakProvider**

Modificar `src/main.jsx`:
```jsx
import React from 'react';
import ReactDOM from 'react-dom/client';
import { ReactKeycloakProvider } from '@react-keycloak/web';
import keycloak from './keycloak';
import App from './App';

const initOptions = {
  onLoad: 'login-required',   // Redireciona para Keycloak se não autenticado
  checkLoginIframe: false,
};

ReactDOM.createRoot(document.getElementById('root')).render(
  <ReactKeycloakProvider authClient={keycloak} initOptions={initOptions}>
    <App />
  </ReactKeycloakProvider>
);
```

- [ ] **Step 5: Usar token nas chamadas à API**

Em qualquer hook/serviço que chama a FastAPI:
```javascript
import { useKeycloak } from '@react-keycloak/web';

function useApi() {
  const { keycloak } = useKeycloak();

  const apiFetch = async (path, options = {}) => {
    const token = keycloak.token;
    const res = await fetch(`${import.meta.env.VITE_API_URL}${path}`, {
      ...options,
      headers: {
        ...options.headers,
        Authorization: `Bearer ${token}`,
        'Content-Type': 'application/json',
      },
    });
    return res.json();
  };

  return { apiFetch };
}
```

- [ ] **Step 6: Remover login form próprio**

Qualquer tela de login própria (com username/password) deve ser removida — Keycloak exibe a tela de login automaticamente via redirect.

- [ ] **Step 7: Commit**

```bash
git add "Sistema de Chamados TI/frontend/"
git commit -m "feat(react): add Keycloak OIDC auth via keycloak-js"
```

---

## Task 7: Limpeza do Banco de Dados

**Files:**
- Create: `src/db/migrations/006_remove_auth_local.sql`
- Modify: `src/db/repository.py` (remover funções não usadas)

**Objetivo:** Remover tabelas de autenticação local que o Keycloak substitui.

- [ ] **Step 1: Criar migration SQL**

Criar `src/db/migrations/006_remove_auth_local.sql`:
```sql
-- Remove auth local substituído pelo Keycloak
-- Executar APÓS confirmar que todos usuários migraram e Keycloak funciona

BEGIN;

-- Remove SSO bridge (não mais necessário com Keycloak)
DROP TABLE IF EXISTS sso_codes CASCADE;

-- Remove sessões locais (Keycloak gerencia sessões)
DROP TABLE IF EXISTS sessoes CASCADE;

-- Remove tokens de reset de senha (Keycloak gerencia password reset)
DROP TABLE IF EXISTS password_reset_tokens CASCADE;

-- Remove colunas de autenticação local da tabela de usuários
-- (manter username, is_admin, email para FKs e referências de auditoria)
ALTER TABLE usuarios_app
  DROP COLUMN IF EXISTS password_hash,
  DROP COLUMN IF EXISTS salt;

-- Garantir que auth_provider registra 'keycloak' para todos
UPDATE usuarios_app SET auth_provider = 'keycloak' WHERE auth_provider = 'local';

COMMIT;
```

- [ ] **Step 2: Executar migration**

```bash
psql $DATABASE_URL -f src/db/migrations/006_remove_auth_local.sql
```

Verificar:
```sql
\dt  -- listar tabelas: sso_codes, sessoes, password_reset_tokens devem sumir
```

- [ ] **Step 3: Remover funções de auth local do repository.py**

Remover de `src/db/repository.py`:
- `_hash_password()` (linhas ~100-130)
- `_verify_password()` (linhas ~133-145)
- `verificar_login()` (linhas 178-209)
- `criar_sessao()` (linhas 430-461)
- `validar_sessao()` (linhas 463-490)
- `encerrar_sessao()` (linhas 493-504)
- `criar_sso_code()` (linhas 366-427)
- `obter_usuario_app_id()` (linhas 338-363)
- `criar_reset_token()` (linhas 2170-2216)
- `validar_reset_token()` (linhas 2219-2240)
- `consumir_reset_token()` (linhas 2243-2277)
- `listar_emails_admins()` (linhas 2149-2167)

Manter:
- `criar_usuario()` — adaptado para não receber senha (apenas username + is_admin)
- `listar_usuarios()`, `excluir_usuario()`, `obter_usuario_por_username()` — ainda úteis

- [ ] **Step 4: Adaptar criar_usuario() para não usar senha**

Substituir a assinatura atual de `criar_usuario()`:
```python
# ANTES:
def criar_usuario(username: str, password: str, is_admin: bool = False) -> bool:

# DEPOIS:
def criar_usuario(username: str, is_admin: bool = False, email: str = "") -> bool:
    """Cria registro local do usuário (sem senha — auth via Keycloak)."""
    with _get_pg_conn() as conn:
        try:
            conn.execute(
                """
                INSERT INTO usuarios_app (username, email, is_admin, auth_provider, ativo)
                VALUES (%s, %s, %s, 'keycloak', TRUE)
                """,
                (username.strip().lower(), email, is_admin),
            )
            return True
        except UniqueViolation:
            return False
```

- [ ] **Step 5: Remover email_service se só usado para password reset**

Verificar:
```bash
grep -rn "send_reset_email\|email_service" app.py src/
```

Se `email_service.py` só era usado para password reset, pode remover o arquivo inteiro.

- [ ] **Step 6: Commit**

```bash
git add src/db/migrations/006_remove_auth_local.sql src/db/repository.py
git commit -m "cleanup: remove local auth tables and functions (replaced by Keycloak)"
```

---

## Task 8: Atualizar Variáveis de Ambiente Finais

**Files:**
- Modify: `.env`

- [ ] **Step 1: .env final consolidado**

Remover:
```env
# COOKIES_PASSWORD=...           (removido)
# JWT_SECRET=...                 (removido)
# JWT_ACCESS_EXPIRES_SECONDS=... (removido)
# JWT_REFRESH_EXPIRES_SECONDS=...  (removido)
```

Adicionar:
```env
# Keycloak SSO
KEYCLOAK_URL=http://192.168.1.100:8080
KEYCLOAK_REALM=prosper
KEYCLOAK_CLIENT_ID_STREAMLIT=streamlit-app
KEYCLOAK_CLIENT_SECRET_STREAMLIT=<secret>
KEYCLOAK_ADMIN_USER=admin
KEYCLOAK_ADMIN_PASSWORD=<senha admin keycloak>

# React (quando frontend existir)
# KEYCLOAK_CLIENT_ID_REACT=chamados-react
```

Manter:
```env
DATABASE_URL=...
CHAMADOS_APP_URL=...
APP_URL=...
ALLOWED_ORIGINS=...
SMTP_*=...
APP_TIMEZONE=...
```

- [ ] **Step 2: Verificar todos os sistemas sobem sem erro**

```bash
# Terminal 1 — Keycloak
cd keycloak && docker compose --env-file .env.keycloak up

# Terminal 2 — FastAPI
cd "Sistema de Chamados TI/backend" && uvicorn app.main:app --reload

# Terminal 3 — Streamlit
streamlit run app.py
```

- [ ] **Step 3: Teste de SSO end-to-end**

1. Abrir Streamlit → login via Keycloak → autenticado
2. Abrir FastAPI docs (`/docs`) → usar token do Keycloak → endpoint protegido responde 200
3. (Quando React existir) Abrir React → login automático via sessão Keycloak → sem pedir login novamente
4. Logout no Streamlit → tentar acessar novamente → pede login

- [ ] **Step 4: Commit final**

```bash
git add .env
git commit -m "config: update env vars for Keycloak SSO (remove JWT_SECRET/COOKIES_PASSWORD)"
```

---

## Resumo de Mudanças

| Sistema | Antes | Depois |
|---------|-------|--------|
| Streamlit | Cookie próprio + bcrypt | streamlit-keycloak OIDC |
| FastAPI | JWT HS256 próprio | JWT RS256 via Keycloak JWKS |
| React (futuro) | Login form → POST /api/auth/login | keycloak-js redirect |
| SSO bridge | sso_code table + endpoint | Keycloak session cookie |
| Usuários | PostgreSQL usuarios_app | Keycloak (espelho em usuarios_app) |
| Password reset | Email interno (SMTP) | Keycloak admin console |
| Sessões | Tabela sessoes no PG | Keycloak session management |

## Ordem de Execução Recomendada

1. Task 1 (Keycloak Docker) → 2 (Realm config) → 3 (Migração usuários)
2. Task 4 (FastAPI) — pode ser paralelo com Task 5
3. Task 5 (Streamlit) 
4. Task 6 (React) — quando frontend existir
5. Task 7 (Limpeza DB) — ÚLTIMO, após confirmar tudo funcionando
6. Task 8 (Env vars) — ao longo de todas as tasks
