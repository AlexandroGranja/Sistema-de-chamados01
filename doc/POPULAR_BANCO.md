# Popular o banco com dados de linhas

O banco novo começa vazio (só usuários). Use uma das opções abaixo.

---

## Opção 1 — Planilhas Excel (recomendado para projeto pessoal)

Planilhas ficam em `data/planilhas/`. O projeto já inclui cópias de referência (importadas do arquivo histórico).

### Importar linhas ativas

```powershell
cd E:\GerenciamentoDeTelefones
python -m scripts.rebuild_ativas_from_primary_sheets
```

Lê `data/planilhas/Telefones11.25_SomenteAtivas.xlsx` (abas Nova Prosper, Norte, Sul, etc.).

### Complemento Diretoria

```powershell
python -m scripts.import_missing_diretoria_lines
```

### Verificar quantidade

```powershell
python -m scripts.verificar_banco
```

No app Streamlit, escolha **Linhas ativas** e o segmento desejado.

---

## Opção 2 — Backup SQLite antigo

Se tiver o arquivo `data/db/gerenciamento_telefones.db` (cópia do sistema antigo):

```powershell
python -m scripts.migrate_sqlite_to_postgres
```

Migra usuários (sem sobrescrever existentes) e linhas ativas/desativadas.

---

## Opção 3 — Dump PostgreSQL da Prosper

Se tiver `.sql` ou `.backup` do servidor antigo:

1. Restaure no pgAdmin ou `pg_restore` / `psql`
2. Use o **mesmo** banco configurado no `.env`
3. Rode `python -m scripts.verificar_banco`

---

## Planilhas disponíveis no projeto

| Arquivo | Uso |
|---------|-----|
| `Telefones11.25_SomenteAtivas.xlsx` | Script `rebuild_ativas_from_primary_sheets` |
| `Telefones11.25.xlsx` | Planilha completa (análise / legado) |
| `Relação Linhas Prosper270226.xlsx` | Referência cruzada de números |

Para dados **mais recentes**, substitua os `.xlsx` em `data/planilhas/` pelos seus arquivos atuais e rode de novo o script de importação.

---

## Chamados (tickets)

Linhas e chamados são independentes. Tickets vazios é normal até abrir chamados no React (localhost:3000).

---

*Relacionado: [[doc/SETUP_BANCO_LOCAL.md]]*
