# Sistema de Chamados TI + Telefonia Corporativa

**Projeto pessoal / portfólio** — plataforma integrada de chamados de TI com módulo de gerenciamento de linhas telefônicas, auditoria unificada e PostgreSQL compartilhado.

> Todos os nomes, números e equipes exibidos são **fictícios** (dados anonimizados). Ver [`doc/DEMO_DADOS_ANONIMIZADOS.md`](doc/DEMO_DADOS_ANONIMIZADOS.md).

---

## O que este projeto faz

Um operador de TI abre um **ticket de telefonia** no React (onboarding, manutenção, desligamento). A API atualiza a **linha** no banco compartilhado, grava **auditoria com `ticket_id`**, e o admin pode abrir o **painel Streamlit** via deep link para edição manual — com retorno ao chamado.

```text
┌─────────────────────────────────────┐
│  Sistema de Chamados TI (principal)   │
│  React · FastAPI · PostgreSQL         │
│  Tickets · fluxos · dashboard         │
└──────────────┬──────────────────────┘
               │  API /telefones · SSO · return_url
               ▼
┌─────────────────────────────────────┐
│  Gerenciamento de Telefones (admin) │
│  Streamlit · grid · histórico       │
└──────────────┬──────────────────────┘
               ▼
        PostgreSQL unificado
   (tickets · linhas · auditoria · users)
```

---

## Stack

| Camada | Tecnologia |
|--------|------------|
| Frontend principal | React, Vite, MUI |
| Backend | FastAPI, SQLAlchemy, Alembic |
| Módulo linhas | Streamlit (admin-only), REST `/api/telefones` |
| Banco | PostgreSQL |
| Integração | SSO (`sso_code`), deep links, auditoria com `ticket_id` |
| Ops local | `ativador_completo.bat`, Docker Compose opcional |

---

## Demo rápida (≈2 min)

### 1. Subir o ambiente

**Windows (recomendado):**

```text
Duplo clique em ativador_completo.bat
```

Sobe:

- React Chamados → http://localhost:3000  
- API FastAPI → http://localhost:8000  
- Streamlit (admin) → http://localhost:8501  

### 2. Login demo

Após rodar a anonimização (ou seed local):

| Usuário | Senha | Uso |
|---------|-------|-----|
| `admin_demo` | `Demo@2026!` | Admin — React + Streamlit |
| `operador_demo` | `Demo@2026!` | Operador — só React |

### 3. Fluxo integrado

1. Login no React → abrir ticket de telefonia  
2. Concluir fluxo que altera linha via API  
3. Clicar link **Ver/editar linha** → Streamlit com `ticket_id` na URL  
4. Conferir **auditoria** com referência ao ticket  

---

## Instalação

### Pré-requisitos

- Python 3.11+
- Node.js 18+ (frontend React)
- PostgreSQL local

### Configuração

1. Copie `.env.example` → `.env` na raiz  
2. Copie `Sistema de Chamados TI/backend/env.example` → `backend/.env` com o **mesmo** `DATABASE_URL`  
3. Crie o banco e schema:

```powershell
python -m scripts.setup_banco_completo
```

4. Anonimize dados para portfólio (recomendado antes de publicar):

```powershell
python -m scripts.anonimizar_dados_demo
python -m scripts.sync_usuarios_chamados
```

Documentação detalhada: [`doc/README.md`](doc/README.md)

---

## Estrutura do monorepo

```
GerenciamentoDeTelefones/
├── app.py, run.py, src/              # Streamlit — linhas (admin)
├── Sistema de Chamados TI/           # React + FastAPI
├── doc/                              # Documentação
├── scripts/                          # Setup, testes E2E, anonimização
├── ativador_completo.bat             # Sobe tudo (dev)
└── docker-compose.stack.yml          # Stack opcional (C5)
```

---

## Testes de integração

```powershell
python -m scripts.smoke_integracao
python -m scripts.test_navegacao_b2_e2e
python -m scripts.test_auditoria_b3_e2e
```

Defina `E2E_LOGIN_PASS=Demo@2026!` para testes que exigem login.

---


## Disclaimer

Sistema desenvolvido e evoluído com arquitetura profissional. Não representa dados, processos ou infraestrutura de empregadores anteriores. Uso educacional e demonstrativo.

---

## Licença

Uso livre para portfólio e estudo. Não inclui planilhas ou dumps com dados reais.
