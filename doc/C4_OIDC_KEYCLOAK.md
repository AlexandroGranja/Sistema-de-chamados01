# OIDC / Keycloak — Fase C4

> **Estado:** PoC integrado no backend React. SSO por `sso_code` (Streamlit → Chamados) **permanece** quando OIDC está desligado.

---

## Modos de login

| Modo | Quando | Fluxo |
|------|--------|-------|
| Senha local | Padrão (`OIDC_ENABLED=false`) | `/api/auth/login` |
| SSO código | Streamlit → Chamados | `sso_codes` + `/api/auth/sso-exchange` |
| OIDC Keycloak | `OIDC_ENABLED=true` | `/api/auth/oidc/login` → callback → JWT |

---

## Variáveis (backend `.env`)

```env
OIDC_ENABLED=false
OIDC_ISSUER=http://localhost:8080/realms/prosper
OIDC_CLIENT_ID=chamados-web
OIDC_CLIENT_SECRET=
OIDC_REDIRECT_URI=http://localhost:8000/api/auth/oidc/callback
OIDC_SCOPES=openid profile email
```

Requisito: usuário OIDC deve existir em **`usuarios_app`** (e-mail ou username igual ao claim Keycloak).

---

## Subir Keycloak (PoC local)

```powershell
docker compose -f docker-compose.keycloak.yml up -d
```

Admin console: http://localhost:8080 (admin / admin — ver compose).

Configure realm `prosper`, client `chamados-web` (public ou confidential), redirect URI acima.

---

## Endpoints API

| Método | Rota | Descrição |
|--------|------|-----------|
| GET | `/api/auth/oidc/status` | `{ enabled, issuer, login_path }` |
| GET | `/api/auth/oidc/login` | Redirect para IdP |
| GET | `/api/auth/oidc/callback` | Troca code → redirect React `?oidc_code=` |
| POST | `/api/auth/oidc/exchange` | `{ oidc_code }` → JWT (uso único) |
| GET | `/api/auth/oidc/logout-url` | URL de logout global Keycloak |

---

## Frontend

- Login TI exibe **Entrar com SSO corporativo** quando `/oidc/status.enabled=true`
- `AuthContext` consome `?oidc_code=` após callback
- Logout chama `/oidc/logout-url` quando OIDC ativo

---

## Teste

```powershell
python -m scripts.test_c4_oidc
```

Com API no ar (`:8000`). Com OIDC desligado, espera `enabled: false`.

---

*Fase C4 — maio/2026. Próximo: C5 deploy unificado.*
