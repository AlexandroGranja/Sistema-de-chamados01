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

## Observação (Fase C2)

No mesmo banco existia a tabela legada **`chamados`** (modelo antigo do Streamlit). O sistema operacional usa **`tickets`** (React).

- **`auditoria.chamado_id`** = **`tickets.id`** em fluxos integrados.
- A tabela `chamados` permanece somente leitura; não abra chamados novos pelo Streamlit.
- Verificação: `python -m scripts.verificar_chamados_legado`
- Migração opcional: `python -m scripts.migrar_chamados_para_tickets --dry-run`
- Documentação completa: [doc/CHAMADOS_TICKETS_UNIFICACAO.md](../../doc/CHAMADOS_TICKETS_UNIFICACAO.md)

## Limpar `users` e manter só o Gerenciamento

Para alinhar a tabela `users` ao cadastro `usuarios_app` (remover órfãos, fundir duplicatas de `snipe_user_id`, reatribuir FKs):

```powershell
# Na raiz do monorepo (recomendado — usa venv do backend):
python -m scripts.sync_usuarios_chamados
python -m scripts.sync_usuarios_chamados --dry-run

# Ou direto no backend:
cd "Sistema de Chamados TI/backend"
python scripts\sync_users_from_usuarios_app.py --dry-run
python scripts\sync_users_from_usuarios_app.py --yes
```

**Automático (Fase B5):** após criar usuário no admin Streamlit ou via `python -m scripts.criar_admin`, o sync roda quando `DATABASE_URL` aponta para PostgreSQL.

**Política de senhas:** [doc/POLITICA_SENHAS.md](../../doc/POLITICA_SENHAS.md) — senha operacional = `usuarios_app`; `users.password_hash` é placeholder bcrypt para contas espelhadas.
