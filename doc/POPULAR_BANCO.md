# Popular o banco com dados de linhas

O banco novo começa vazio (só usuários). Use uma das opções abaixo.

---

## Opção 1 — Planilhas Excel (local, não versionadas)

Planilhas ficam em `data/planilhas/` (**fora do Git**). Use arquivos locais ou o banco já populado + anonimização.

```powershell
cd E:\GerenciamentoDeTelefones
python -m scripts.rebuild_ativas_from_primary_sheets
```

Lê `data/planilhas/Telefones11.25_SomenteAtivas.xlsx` (abas fictícias ou anonimizadas).

### Anonimizar para portfólio público

```powershell
python -m scripts.anonimizar_dados_demo
python -m scripts.sync_usuarios_chamados
```

Ver [`DEMO_DADOS_ANONIMIZADOS.md`](./DEMO_DADOS_ANONIMIZADOS.md).

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

## Opção 3 — Restaurar backup local (não versionado)

Se tiver dump `.sql` ou `.backup` **seu** (local):

1. Restaure no pgAdmin ou `pg_restore` / `psql`
2. Use o **mesmo** banco configurado no `.env`
3. Rode `python -m scripts.verificar_banco`

---

## Planilhas (locais)

| Arquivo | Uso |
|---------|-----|
| `Telefones11.25_SomenteAtivas.xlsx` | Script `rebuild_ativas_from_primary_sheets` |
| Outros `.xlsx` | Análise / legado — **não commitar** |

Substitua os arquivos em `data/planilhas/` localmente e rode o script de importação. Depois anonimize com `scripts.anonimizar_dados_demo`.

---

## Chamados (tickets)

Linhas e chamados são independentes. Tickets vazios é normal até abrir chamados no React (localhost:3000).

---

*Relacionado: [[doc/SETUP_BANCO_LOCAL.md]]*
