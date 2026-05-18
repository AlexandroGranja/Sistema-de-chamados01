# Sistema de Chamados Prosper

Sistema interno para abertura, acompanhamento e encerramento de chamados de TI, com fluxo de desligamento e integracao com Snipe-IT.

## Cadastro publico (link para colaboradores)

Para que **qualquer pessoa** abra chamado direto com a TI, sem acesso ao painel interno:

| URL | Descricao |
|-----|-----------|
| `/cadastro` | Formulario: **nome, sobrenome, e-mail, setor, senha e repetir senha** |
| `/portal/login` | Entrada com **e-mail e senha** (mesmo cadastro) |
| `/portal/novo-chamado` | Formulario de novo chamado (apos login) |

- Administradores veem esses usuarios em **Usuarios** (secao *Usuarios do cadastro publico*) e os chamados em **Chamados** como os demais (titulo, descricao, data de abertura, solicitante).
- No **PostgreSQL unificado** com `usuarios_app`, o cadastro cria tambem uma linha la para manter a chave dos chamados (`solicitante_id`). Rode `alembic upgrade head` para incluir o valor de papel `requester` no enum, se aplicavel.
- **Login legado por telefone:** em `backend/.env`, `PORTAL_DEFAULT_DDD` ainda e usado se alguem entrar digitando so o numero local (cadastros antigos); novos cadastros usam **e-mail**.

## Stack

- Backend: FastAPI + SQLAlchemy + Alembic
- Frontend: React + Vite + MUI
- Banco: **PostgreSQL** (padrao; SQLite ainda suportado para testes)

## Estrutura

```txt
Sistema de Chamados TI/
|- doc/
|- backend/
|- frontend/
|- docker-compose.yml   (PostgreSQL opcional)
|- ativador.bat
`- README.md
```

## Pre-requisitos

- Python 3.10+
- Node.js 18+
- npm 9+
- **PostgreSQL** (local ou remoto), ou [Docker](https://www.docker.com/) para subir o `docker-compose.yml`

## Ambiente local (Windows/PowerShell)

Use **dois terminais**: um para backend e outro para frontend.

### 1) Backend – passo a passo recomendado (Python 3.10)

> Importante: este projeto foi testado com **Python 3.10**. Versoes 3.11+ podem gerar erro em `pydantic_core`.

```powershell
# 1. Ir para a pasta do backend
cd "c:\Users\TI02\Desktop\Sistema de Chamados TI\backend"

# 2. (Opcional) remover um venv antigo se estiver quebrado
Remove-Item -Recurse -Force .\venv  # ignore erro se nao existir

# 3. Criar venv usando explicitamente o Python 3.10
"C:\Users\TI02\AppData\Local\Programs\Python\Python310\python.exe" -m venv venv

# 4. Ativar o venv
.\venv\Scripts\Activate.ps1

# 5. Instalar dependencias
pip install -r requirements.txt

# 6. Configurar backend/.env (copie de env.example) — DATABASE_URL apontando para o PostgreSQL

# 7. Criar tabelas (opcional; o startup tambem cria se necessario)
alembic upgrade head

# 8. (Opcional) criar usuario admin inicial — ou use o usuario suporte ja definido na sua base
python scripts\create_admin.py

# 9. Subir o backend
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

Backend:

- API: `http://localhost:8000`
- Swagger: `http://localhost:8000/api/docs`

### 2) Frontend – passo a passo

```powershell
# 1. Ir para a pasta do frontend
cd "c:\Users\TI02\Desktop\Sistema de Chamados TI\frontend"

# 2. Instalar dependencias (apenas na primeira vez ou apos atualizar pacotes)
npm install

# 3. Subir o frontend em modo desenvolvimento
npm run dev
```

Frontend:

- App: `http://localhost:3000` (ou porta exibida pelo Vite)

### 3) Uso do script `.bat` (ativador completo)

Script principal:

- `ativador.bat`: instala dependencias e inicia o sistema completo
  - cria/ativa `backend\venv` com Python 3.10 (quando necessario); se voce usar outro venv na **raiz** (`.venv`), ative esse antes de rodar scripts em `backend` — nao existe `backend\venv` ate o ativador criar.
  - instala dependencias backend (`pip install -r backend\requirements.txt`);
  - instala dependencias frontend (`npm install`, quando necessario);
  - abre **duas janelas**:
    - `Backend - Sistema de Chamados Prosper` com `uvicorn`;
    - `Frontend - Sistema de Chamados Prosper` com `npm run dev`.

Execucao no PowerShell:

```powershell
cd "c:\Users\TI02\Desktop\Sistema de Chamados TI"
.\ativador.bat
```

## Configuracao de ambiente

### Backend (`backend/.env`)

Copie `backend/env.example` para `backend/.env` e ajuste.

Minimo para PostgreSQL local (exemplo alinhado ao `docker-compose.yml`):

```env
DATABASE_URL=postgresql://chamados:chamados@localhost:5432/chamados_ti
SECRET_KEY=troque_esta_chave
JWT_ALGORITHM=HS256
JWT_EXPIRATION=3600
JWT_REFRESH_EXPIRATION=86400
```

SQLite (apenas desenvolvimento legado):

```env
DATABASE_URL=sqlite:///./chamados.db
```

Detalhes e instalacao do PostgreSQL: **`doc/POSTGRES.md`**.

Para subir o PostgreSQL com Docker (na raiz do projeto):

```powershell
docker compose up -d
```

Para integrar com Snipe-IT:

```env
SNIPE_BASE_URL=http://SEU_SERVIDOR_SNIPE:8082
SNIPE_API_TOKEN=SEU_TOKEN
SNIPE_STATUS_READY_ID=2
SNIPE_STATUS_MAINTENANCE_ID=3

# Integracao opcional com Gerenciamento de Telefones
TELEFONES_SYNC_ENABLED=True
TELEFONES_DB_PATH=C:\Users\TI02\Desktop\Planilhas Telefones\data\db\gerenciamento_telefones.db
```

### Frontend (`frontend/.env`)

Opcoes:

1. Usar proxy do Vite (recomendado local):

```env
VITE_API_URL=
```

1. Chamada direta para backend:

```env
VITE_API_URL=http://localhost:8000
```

## Usuario principal (padrao atual)

- Email: `suporte@prosperdistribuidora.com.br`
- Senha: definida no ultimo reset (veja abaixo) ou troque pelo painel apos logar

### Resetar usuarios (manter somente suporte como admin)

Remove os demais usuarios e mantem apenas `suporte@prosperdistribuidora.com.br` com perfil **ADMIN** (senha temporaria no final do comando). Funciona com **PostgreSQL** (`DATABASE_URL` no `backend/.env`) ou com arquivo **SQLite** (caminho opcional).

```powershell
cd "c:\Users\TI02\Desktop\Sistema de Chamados TI\backend"
.\venv\Scripts\Activate.ps1
python scripts\reset_usuarios_somente_suporte.py
```

Opcional — apenas SQLite em arquivo:

```powershell
python scripts\reset_usuarios_somente_suporte.py "C:\caminho\chamados.db"
```

### Criar usuario admin generico (script antigo)

```powershell
python scripts\create_admin.py
```

Cria/atualiza `admin@promio.com.br` / `admin123` (troque em producao).

## Problemas comuns

### Backend nao sobe

- Garanta que o venv foi ativado: `.\venv\Scripts\Activate.ps1`
- Verifique dependencias: `pip install -r requirements.txt`
- Confira porta 8000 em uso por outro processo

### Frontend nao conecta no backend

- Backend deve estar rodando na porta 8000
- Verifique `frontend/.env` (`VITE_API_URL`)
- Reinicie o Vite apos mudar `.env`

### Erro de autenticacao/login

- Confira `DATABASE_URL` no `backend/.env` e se o PostgreSQL esta acessivel (`docker compose ps` ou servico Windows)
- Rode: `python scripts\create_admin.py` (cria `admin@promio.com.br` se nao existir)
- Se usar SQLite: confirme se o caminho em `DATABASE_URL` e a pasta de onde o `uvicorn` foi iniciado batem com o arquivo `.db`
- **Senha incorreta (401):** existem **duas** senhas possiveis no banco unificado: (1) a do **Gerenciamento de Telefones** (`usuarios_app`) e (2) a do **Chamados** (hash em `users`, ex.: troca de senha no sistema). Com **e-mail** no login, o backend tenta **primeiro** a senha do Chamados; se nao bater, tenta o fluxo do Gerenciamento. Use o **mesmo e-mail** cadastrado na tabela `users` (pode ser sintetico `*@example.com` se ainda nao sincronizou).

## Deploy em servidor (producao)

Resumo recomendado (Ubuntu):

1. Subir backend com `uvicorn` via `systemd`
2. Gerar build do frontend com `npm run build`
3. Servir frontend e proxy `/api` com Nginx
4. Usar PostgreSQL em producao
5. Configurar HTTPS (Lets Encrypt)

### Exemplo rapido de fluxo

```bash
# backend
cd /opt/sistema-chamados/backend
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
alembic upgrade head

# frontend
cd /opt/sistema-chamados/frontend
npm ci
npm run build
```

Depois:

- `backend` como servico `systemd` (porta interna, ex. 8000)
- `frontend/dist` servido pelo Nginx
- Nginx fazendo proxy de `/api` para `http://127.0.0.1:8000`

## READMEs por modulo

- Backend detalhado: `backend/README.md`
- Frontend detalhado: `frontend/README.md`

## Documentacao interna

- **Banco unificado** (mesmo PostgreSQL + mesmo login do Gerenciamento de Telefones): `doc/BANCO_UNIFICADO.md`
- PostgreSQL (instalacao, Docker, URL): `doc/POSTGRES.md`
- Planejamento de integracao telefonia: `doc/PLANO_INTEGRACAO_TELEFONES.md`
- Guias e mapeamentos do projeto: pasta `doc/`

