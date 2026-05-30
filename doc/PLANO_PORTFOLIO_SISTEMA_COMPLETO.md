# Plano mestre — Sistema completo para portfólio

> **Contexto:** projeto pessoal / portfólio (pós-Prosper).  
> **Produto principal:** **Sistema de Chamados TI** (React + FastAPI).  
> **Diferencial:** integração nativa com **Gerenciamento de Telefones** (linhas, auditoria, ciclo de vida).

---

## Visão do produto

```text
                    ┌─────────────────────────────────────┐
                    │   SISTEMA DE CHAMADOS TI (principal) │
                    │   React · FastAPI · PostgreSQL       │
                    │   Tickets · fluxos · dashboard       │
                    └──────────────┬──────────────────────┘
                                   │
              API /telefones       │  deep links + SSO
              auditoria ticket_id  │
                                   ▼
                    ┌─────────────────────────────────────┐
                    │   GERENCIAMENTO DE TELEFONES         │
                    │   Streamlit · painel de linhas       │
                    │   consulta em massa · histórico admin│
                    └─────────────────────────────────────┘
                                   │
                                   ▼
                         PostgreSQL unificado
                    (tickets · linhas · auditoria · users)
```

**Narrativa de portfólio:**  
*"Plataforma de chamados de TI com módulo integrado de telefonia corporativa — um ticket dispara onboarding, manutenção ou desligamento de linha, com rastreabilidade completa no banco."*

---

## O que já está pronto

| Área | Status |
|------|--------|
| Monorepo organizado (Fase A) | ✅ |
| PostgreSQL local + scripts setup | ✅ |
| Chamados: tickets, fluxos telefonia, Snipe-IT (opcional) | ✅ |
| Gerenciamento: linhas, segmentos, auditoria | ✅ |
| Login compartilhado (`usuarios_app`) | ✅ |
| B1 parcial: `tickets.id` na auditoria Streamlit | ✅ código |
| Dados demo (planilhas → 84 linhas ativas) | ✅ |
| Ativador completo corrigido | ✅ |

---

## Roadmap em 4 macro-fases

Continuamos o trabalho **B → C** já planejado e acrescentamos **D (portfólio)**.

---

### Fase B — Integração operacional *(em andamento)*

**Meta:** o operador vive no **Chamados**; o Gerenciamento entra só quando precisa editar linha manualmente. Tudo rastreável ao `ticket_id`.

| # | Entrega | Prioridade | Esforço |
|---|---------|------------|---------|
| B1 | Validar `tickets.id` na auditoria (teste E2E + link no histórico) | Alta | 1–2 dias |
| B3 | Auditoria quando API `/telefones/*` altera linhas | Alta | 3–5 dias |
| B2 | Links bidirecionais Chamados ↔ Gerenciamento (SSO + `return_url`) | Alta | 3–5 dias |
| B5 | Sync estável `usuarios_app` ↔ `users` | Média | 1–2 dias |
| B4 | Matriz “qual app usar” + smoke test | Média | 1 dia |

**Demo portfólio mínima (após B2+B3):**  
1. Abrir ticket de onboarding no Chamados  
2. Sistema atualiza linha via API  
3. Clicar “Ver/editar linha” → Gerenciamento com contexto do ticket  
4. Mostrar auditoria com `ticket_id`

**Referência técnica:** `doc/PLANO_FASES_BC_INTEGRACAO.md`

---

### Fase C — Consolidação técnica

**Meta:** uma fonte de verdade, menos duplicidade, código apresentável em entrevista.

| # | Entrega | Benefício |
|---|---------|-----------|
| C1 | Regras de `linhas` centralizadas no FastAPI (Streamlit consome API com flag) | Arquitetura limpa |
| C2 | Deprecar tabela/UI `chamados` legado no Streamlit | Um modelo de ticket |
| C3 | Gerenciamento = **módulo admin** (não segundo produto) | Narrativa clara |
| C4 | Docker Compose raiz (postgres + api + web + streamlit opcional) | Deploy reproduzível |
| C5 | README técnico + diagrama de arquitetura | Portfólio |

**Decisão de produto (C3):**  
- **Chamados** = 100% do fluxo do usuário final  
- **Gerenciamento** = painel complementar (grid, histórico bruto, config) — documentar assim no README

---

### Fase D — Portfólio e apresentação

**Meta:** projeto “completo” para GitHub, LinkedIn e entrevistas.

| # | Entrega | Detalhe |
|---|---------|---------|
| D1 | **README principal** orientado a Chamados + seção Integração Telefonia | Hero: stack, screenshot, fluxo |
| D2 | **Dados demo anonimizados** | Nomes/equipes fictícios ou genéricos; seed script |
| D3 | **Screenshots / GIF** | 3 cenas: dashboard, fluxo linha, auditoria |
| D4 | **Vídeo curto ou walkthrough** | 2–3 min mostrando integração |
| D5 | **Deploy opcional** | Railway/Render/VPS — pelo menos API + frontend |
| D6 | **Case study** (Obsidian + 1 página markdown) | Problema → solução → stack → resultado |

**Tom do portfólio:** sistema real construído em ambiente corporativo, evoluído para projeto pessoal open/private com arquitetura profissional.

---

### Fase E — Melhorias pós-MVP *(depois que B+C+D estiverem sólidos)*

Só entrar aqui quando você quiser “polir” além do necessário para portfólio.

| Área | Ideias |
|------|--------|
| UX Chamados | Redesign já esboçado em docs; unificar visual Prosper |
| Telefonia no React | Grid de linhas dentro do Chamados (reduzir dependência Streamlit) |
| Notificações | E-mail / in-app para ticket + linha |
| SSO | Keycloak/Azure AD (doc arquivado em `_archive/`) |
| Testes | pytest API + Playwright fluxos críticos |
| Snipe-IT | Mock ou sandbox para demo sem empresa |

---

## Ordem de execução recomendada

```text
[B1 validar] → [B3 auditoria API] → [B2 navegação] → [B5 usuários]
        ↓
[C2 modelo ticket único] → [C4 docker] → [C5 README técnico]
        ↓
[D1 README portfólio] → [D2 seed demo] → [D3 screenshots] → [D5 deploy opcional]
        ↓
[E melhorias conforme feedback]
```

**Próxima sessão de código sugerida:** **B3** (auditoria nas mutações via API) — maior impacto visível na integração Chamados ↔ linhas.

---

## Critérios de “sistema completo” (Definition of Done)

- [ ] Operador abre e resolve ticket **só pelo Chamados** nos fluxos de linha
- [ ] Toda alteração de linha ligada a um ticket grava **auditoria com `ticket_id`**
- [ ] Link explícito Chamados → Gerenciamento → voltar ao ticket
- [ ] Um comando sobe o ambiente (`ativador_completo.bat` ou `docker compose up`)
- [ ] README explica arquitetura em 5 minutos
- [ ] Dados demo permitem testar sem informação real da Prosper
- [ ] Repositório privado/público com histórico de commits coerente

---

## Stack para destacar no portfólio

| Camada | Tecnologia |
|--------|------------|
| Frontend principal | React, Vite, MUI |
| Backend | FastAPI, SQLAlchemy, Alembic |
| Módulo linhas | Streamlit (admin), PostgreSQL compartilhado |
| Banco | PostgreSQL |
| Integração | REST `/api/telefones`, SSO, auditoria unificada |
| Ops | Docker, scripts Python, `.bat` local |

---

## Documentos relacionados

| Arquivo | Conteúdo |
|---------|----------|
| [PLANO_FASES_BC_INTEGRACAO.md](./PLANO_FASES_BC_INTEGRACAO.md) | Detalhe técnico B e C |
| [ARQUITETURA_SISTEMA_UNIFICADO.md](./ARQUITETURA_SISTEMA_UNIFICADO.md) | Visão alvo de banco/backend |
| [SETUP_BANCO_LOCAL.md](./SETUP_BANCO_LOCAL.md) | Ambiente local |
| [POPULAR_BANCO.md](./POPULAR_BANCO.md) | Importar linhas demo |

---

*Criado: maio/2026 — projeto portfólio, Chamados como sistema principal.*
