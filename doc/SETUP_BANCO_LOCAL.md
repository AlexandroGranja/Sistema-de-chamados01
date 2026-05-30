# Setup do banco PostgreSQL local (projeto pessoal)

Este guia assume que o sistema saiu do ambiente Prosper e roda no **seu PostgreSQL local** (PC).

---

## Visão geral

| App | Arquivo `.env` | Variável principal |
|-----|----------------|-------------------|
| Gerenciamento (Streamlit) | `.env` na **raiz** | `DATABASE_URL` |
| Chamados (FastAPI) | `Sistema de Chamados TI/backend/.env` | **mesmo** `DATABASE_URL` |

Os dois apps compartilham **um banco**. Nome sugerido: `gerenciamento_telefones`.

---

## Opção 1 — PostgreSQL já instalado no Windows

### 1. Criar banco e usuário

Abra **pgAdmin** ou o SQL Shell (`psql`) e execute (ajuste senha):

```sql
CREATE USER telefones WITH PASSWORD 'sua_senha_segura';
CREATE DATABASE gerenciamento_telefones OWNER telefones;
GRANT ALL PRIVILEGES ON DATABASE gerenciamento_telefones TO telefones;
```

### 2. Configurar `.env`

Na raiz do projeto, copie `.env.example` → `.env`:

```env
DATABASE_URL=postgresql://telefones:sua_senha_segura@localhost:5432/gerenciamento_telefones
CHAMADOS_APP_URL=http://localhost:3000
APP_TIMEZONE=America/Sao_Paulo
```

Copie também `Sistema de Chamados TI/backend/env.example` → `backend/.env` com o **mesmo** `DATABASE_URL`.

> **Senha com caracteres especiais:** use URL encoding (`$` → `%24`, `@` → `%40`).

### 3. Criar tabelas

```powershell
cd E:\GerenciamentoDeTelefones
python -m venv .venv
.\.venv\Scripts\pip install -r requirements.txt
python -m scripts.init_postgres
```

No backend dos Chamados:

```powershell
cd "E:\GerenciamentoDeTelefones\Sistema de Chamados TI\backend"
python -m venv venv
.\venv\Scripts\pip install -r requirements.txt
.\venv\Scripts\alembic.exe upgrade head
```

### 4. Verificar

```powershell
cd E:\GerenciamentoDeTelefones
python -m scripts.verificar_banco
```

---

## Opção 2 — Docker (se tiver Docker Desktop)

Na raiz do projeto:

```powershell
docker compose up -d
```

Use no `.env`:

```env
DATABASE_URL=postgresql://telefones:telefones@localhost:5432/gerenciamento_telefones
```

Depois siga os passos 3 e 4 acima.

---

## Trazer dados antigos (Prosper / backup)

### A) Dump `.sql` ou `.backup` do PostgreSQL

```powershell
# Exemplo com pg_restore (ajuste caminho e credenciais)
pg_restore -h localhost -U telefones -d gerenciamento_telefones C:\backup\prosper.dump
```

Ou via pgAdmin: botão direito no banco → Restore.

Depois rode `python -m scripts.verificar_banco` e, se faltar tabela `tickets`, `alembic upgrade head`.

### B) SQLite legado local (`data/db/gerenciamento_telefones.db`)

Se ainda tiver o arquivo `.db` antigo:

```powershell
python -m scripts.migrate_sqlite_to_postgres
```

### C) Banco vazio (começar do zero)

1. `python -m scripts.init_postgres`
2. `alembic upgrade head`
3. Crie admin na primeira execução do Streamlit ou `python -m scripts.criar_admin`

---

## MCP e Cursor — consigo conectar o agente ao PostgreSQL?

**Hoje, não diretamente.** Os MCPs habilitados no seu Cursor incluem Obsidian, GitHub, Playwright, Outlook etc., mas **não há servidor MCP de PostgreSQL** configurado.

Alternativas:

| Forma | O que o agente consegue fazer |
|-------|-------------------------------|
| **Terminal + Python/psql** | Rodar `verificar_banco`, migrations, scripts (como agora) |
| **Adicionar MCP Postgres** | Instalar um MCP como `@modelcontextprotocol/server-postgres` no Cursor Settings → MCP |
| **pgAdmin / DBeaver** | Você consulta manualmente; o agente orienta os SQLs |

Se quiser MCP Postgres, adicione no Cursor (exemplo):

```json
{
  "mcpServers": {
    "postgres": {
      "command": "npx",
      "args": ["-y", "@modelcontextprotocol/server-postgres", "postgresql://telefones:SENHA@localhost:5432/gerenciamento_telefones"]
    }
  }
}
```

> Troque a URL pela sua. Evite commitar senha no repositório.

---

## Checklist rápido

- [ ] PostgreSQL rodando (serviço Windows ou Docker)
- [ ] `.env` na raiz com `DATABASE_URL`
- [ ] `backend/.env` com o **mesmo** `DATABASE_URL`
- [ ] `python -m scripts.init_postgres`
- [ ] `alembic upgrade head` no backend
- [ ] `python -m scripts.verificar_banco` → tabelas OK
- [ ] `python -m scripts.criar_admin` (se banco novo, sem usuários)
- [ ] `ativador_completo.bat` sobe os 3 serviços

### Setup automático (Windows + PostgreSQL 17)

Se o PostgreSQL já está instalado e você sabe a senha do superuser `postgres`:

```powershell
cd E:\GerenciamentoDeTelefones
powershell -ExecutionPolicy Bypass -File scripts\setup_banco_local.ps1
```

O script pede senhas, cria banco/usuário, grava `.env` e roda `init_postgres` + `alembic`.

---

*Relacionado: [[doc/README.md]], Fase B1 em [[doc/PLANO_FASES_BC_INTEGRACAO.md]]*
