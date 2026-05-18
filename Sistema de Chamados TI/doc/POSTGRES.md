# PostgreSQL – Sistema de Chamados Prosper

O backend usa **`DATABASE_URL`** no arquivo `backend/.env`. O padrão no código aponta para PostgreSQL local.

## Opção A – Docker (rápido no Windows)

Na raiz do projeto:

```powershell
docker compose up -d
```

Aguarde o container ficar saudável. Em `backend/.env`:

```env
DATABASE_URL=postgresql://chamados:chamados@localhost:5432/chamados_ti
```

> Troque usuário/senha em produção. No `docker-compose.yml` os valores padrão são `chamados` / `chamados`.

## Opção B – PostgreSQL instalado no Windows

1. Instale o PostgreSQL (ex.: 15 ou 16).
2. Crie banco e usuário (exemplo no **pgAdmin** ou `psql`):

```sql
CREATE USER chamados WITH PASSWORD 'sua_senha_segura';
CREATE DATABASE chamados_ti OWNER chamados;
```

3. Em `backend/.env`:

```env
DATABASE_URL=postgresql://chamados:sua_senha_segura@localhost:5432/chamados_ti
```

### Caracteres especiais na senha

Se a senha tiver `@`, `#`, espaços etc., use **URL encoding** na URL ou defina a senha só com caracteres seguros para URL. O backend normaliza a URL para evitar erros comuns no Windows.

**Importante (arquivo `.env`):** o caractere **`$`** na senha é interpretado pelo `python-dotenv` como início de variável e **corta** a senha (ex.: `abc$xyz` vira só `abc`). Troque `$` por **`%24`** na URL, por exemplo:

```env
# Senha real: minha$senha
DATABASE_URL=postgresql://postgres:minha%24senha@localhost:5432/meu_banco
```

O backend **decodifica** `%24` com `unquote` antes de reconectar (evita senha errada tipo `minha%2524senha`).

## Criar tabelas

Com o venv ativado na pasta `backend`:

```powershell
alembic upgrade head
```

Na primeira subida, o FastAPI também executa `create_all` se necessário.

## Migração a partir do SQLite antigo

1. Exporte/importe com ferramentas (ex.: `pgloader`, backup CSV) ou mantenha o SQLite só em desenvolvimento.
2. Para testar só o PostgreSQL vazio: ajuste `DATABASE_URL`, suba o backend e crie o usuário com `python scripts\create_admin.py` ou pelo painel.

## Voltar a usar SQLite (desenvolvimento)

Em `backend/.env`:

```env
DATABASE_URL=sqlite:///./chamados.db
```

SQLite continua suportado pelo mesmo código.
