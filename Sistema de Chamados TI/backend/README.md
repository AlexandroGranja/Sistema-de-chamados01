# Backend - Sistema de Chamados Prosper

API FastAPI responsavel por autenticacao, usuarios, chamados e integracao com Snipe-IT.

## Requisitos

- Python 3.10+
- pip
- **PostgreSQL** (recomendado) ou SQLite (desenvolvimento)

## Variaveis de ambiente

Copie `env.example` para `.env`. O padrao do codigo e PostgreSQL (`DATABASE_URL`).

Veja **`../doc/POSTGRES.md`** para Docker, criacao de banco e alternativas.

## Subir local (Windows/PowerShell)

```powershell
cd "c:\Users\TI02\Desktop\Sistema de Chamados TI\backend"
python -m venv venv
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt
# Configure .env (DATABASE_URL, SECRET_KEY, etc.)
alembic upgrade head
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

URLs:

- API: `http://localhost:8000`
- Docs: `http://localhost:8000/api/docs`

## Alertas de chamados (portal)

- `GET /api/tickets/staff-requester-alerts` — **admin/técnico**: lista chamados do cadastro público (`requester`) ainda **não encerrados** (não resolved/closed/cancelled). O painel usa polling + som (novo ID) + aviso flutuante até o chamado ser atualizado para status final.

## Banco e migrations

```powershell
alembic upgrade head
```

Na primeira subida, o FastAPI tambem executa `create_all` se necessario.

## Usuario admin inicial (script opcional)

```powershell
python scripts\create_admin.py
```

Cria `admin@promio.com.br` / `admin123` se ainda nao existir.

## Producao (resumo)

- Definir `DATABASE_URL` para PostgreSQL no servidor
- `alembic upgrade head`
- Subir com `systemd` + `uvicorn`
- Expor via Nginx com proxy para `127.0.0.1:8000`
