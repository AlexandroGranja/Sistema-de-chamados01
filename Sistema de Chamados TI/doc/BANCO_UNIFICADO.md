# Banco unificado: Gerenciamento de Telefones + Sistema de Chamados

## Ideia

Um **único PostgreSQL** concentra:

- Cadastro e login: tabela **`usuarios_app`** (mesmo usuário e **mesma senha** do app Streamlit).
- Linhas de telefonia: **`linhas`**, SSO: **`sso_codes`**, etc. (schema em `Planilhas Telefones/src/db/schema_postgres.sql`).
- Chamados (API FastAPI): tabelas **`users`**, **`tickets`**, comentários, histórico, etc.

O backend de chamados usa a mesma variável **`DATABASE_URL`** que o projeto **Planilhas Telefones** (`.env` na pasta do Gerenciamento ou variável de ambiente no servidor).

## Login único

1. O usuário digita **e-mail ou nome de usuário** e a **senha** iguais aos do Gerenciamento de Telefones.
2. A API valida em **`usuarios_app`** com o mesmo algoritmo de senha (SHA256 de `salt + senha`).
3. É criada/atualizada uma linha na tabela **`users`** (chamados) com `snipe_user_id` = `usuarios_app.id`, para manter chaves estrangeiras nos chamados.
4. O fluxo **SSO** (código descartável) continua disponível para abrir o Chamados a partir do Streamlit.

## Configuração (`backend/.env`)

```env
# Mesma URL do PostgreSQL do Gerenciamento de Telefones
DATABASE_URL=postgresql://usuario:senha@localhost:5432/SEU_BANCO

# Com PostgreSQL unificado, a integração de desligamento usa o mesmo banco.
# TELEFONES_DB_PATH pode ficar vazio (o código ignora o SQLite quando DATABASE_URL é PostgreSQL).
TELEFONES_SYNC_ENABLED=True
TELEFONES_DB_PATH=
```

## Tabelas

- **`usuarios_app`**: fonte da verdade para credenciais compartilhadas.
- **`users`**: espelho operacional do app React (JWT, FK em tickets). Não substitui o login; senha bcrypt aqui é placeholder quando o usuário veio do SSO/login unificado.

## Migração a partir do SQLite antigo (só chamados)

1. Suba o PostgreSQL unificado e rode o `init` do Gerenciamento se ainda não existir o schema.
2. Aponte `DATABASE_URL` do backend de chamados para esse banco.
3. Suba o backend: `create_all` / `alembic upgrade head` criam `users`, `tickets`, etc.
4. (Opcional) Importar dados antigos de `chamados.db` com ferramenta de ETL ou script dedicado — não há migração automática única no repositório.

## Observação

No mesmo banco existe também a tabela legada **`chamados`** (modelo do Streamlit). O sistema React usa a tabela **`tickets`**. São conviventes; não confundir nomes.

## Limpar `users` e manter só o Gerenciamento

Para alinhar a tabela `users` ao cadastro `usuarios_app` (remover órfãos, fundir duplicatas de `snipe_user_id`, reatribuir FKs):

```powershell
# 1) Ative o venv (use o que existir no seu PC):
#    Raiz:  & .\.venv\Scripts\Activate.ps1
#    Ou, se o ativador criou só em backend:  cd backend ; .\venv\Scripts\Activate.ps1

cd backend
python scripts\sync_users_from_usuarios_app.py --dry-run
python scripts\sync_users_from_usuarios_app.py --yes
```
