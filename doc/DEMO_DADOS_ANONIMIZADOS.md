# Dados demo anonimizados

Este repositório é **projeto pessoal / portfólio**. Nenhum dado real de empresa ou colaborador deve ser commitado.

## O que foi anonimizado

| Tipo | Tratamento |
|------|------------|
| Nomes de pessoas | Nomes fictícios determinísticos |
| Telefones / linhas | Padrão `2199000XXXX` (fictício) |
| E-mails | `@demo.example` |
| IMEI / patrimônio sensível | Sequências fictícias |
| Equipes / abas | `Prosper *` → `Distrito *` / `Centro Alimentos` |
| Usuários de login | Contas demo padronizadas |

## Contas demo (após rodar o script)

| Usuário | Senha | Papel |
|---------|-------|-------|
| `admin_demo` | `Demo@2026!` | Admin (Streamlit + Chamados) |
| `operador_demo` | `Demo@2026!` | Operador (só React) |

## Como aplicar

```powershell
cd E:\GerenciamentoDeTelefones
# .env com DATABASE_URL configurado
python -m scripts.anonimizar_dados_demo
python -m scripts.sync_usuarios_chamados
```

Simulação (sem gravar):

```powershell
python -m scripts.anonimizar_dados_demo --dry-run
```

Só CSVs de equipes:

```powershell
python -m scripts.anonimizar_dados_demo --csv-only
```

## Arquivos que **não** entram no Git

- `.env` e `backend/.env`
- Planilhas Excel (`data/planilhas/*.xlsx`)
- Backups PostgreSQL (`backups/`)
- Bancos SQLite locais (`*.db`)

Para popular linhas demo sem planilha real, use o banco já anonimizado ou importe planilhas **fictícias** locais (não versionadas).

## Disclaimer

Sistema desenvolvido originalmente em contexto corporativo e evoluído como projeto pessoal com arquitetura profissional. Marcas, nomes e números exibidos são **fictícios**.
