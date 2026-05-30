# Deploy unificado — Fase C5

> Stack Docker opcional para dev/staging com nginx na porta **8088**.

---

## Componentes

| Serviço | Container | Rota nginx |
|---------|-----------|------------|
| PostgreSQL | `gt_stack_postgres` | (interno) |
| API FastAPI | `gt_stack_api` | `/api/` |
| React (build) | `gt_stack_web` | `/chamados/` |
| Streamlit | `gt_stack_streamlit` | `/telefones/` |
| Nginx | `gt_stack_nginx` | `:8088` |

---

## Subir stack

```powershell
# 1. Postgres so (dev local sem Docker app)
docker compose up -d

# 2. Stack completo
copy deploy\stack.env.example deploy\stack.env
docker compose -f docker-compose.stack.yml up -d --build
```

URLs:

- Chamados: http://localhost:8088/chamados/
- Gerenciamento: http://localhost:8088/telefones/
- API: http://localhost:8088/api/

Validar compose:

```powershell
python -m scripts.validate_compose_stack
```

---

## Backup PostgreSQL

```powershell
python -m scripts.backup_postgres
python -m scripts.backup_postgres --output backups\manual.dump
```

Usa `DATABASE_URL` do `.env` raiz. Requer `pg_dump` no PATH.

---

## Healthchecks

Todos os serviços críticos no `docker-compose.stack.yml` expõem healthcheck (postgres, api).

Smoke local (sem Docker app):

```powershell
python -m scripts.smoke_integracao
```

---

## Produção

- Troque `SECRET_KEY`, senhas Postgres e configure TLS no nginx
- Ative OIDC (`doc/C4_OIDC_KEYCLOAK.md`) se usar Keycloak corporativo
- Mantenha `STREAMLIT_ADMIN_ONLY=true` (Fase C3)

---

*Fase C5 — maio/2026.*
