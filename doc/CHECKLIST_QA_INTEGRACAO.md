# Checklist QA — Integração Gerenciamento + Chamados

Use após subir os três serviços (`ativador_completo.bat` ou URLs abaixo).

**URLs locais:** Gerenciamento `:8501` · Chamados web `:3000` · API `:8000`

**Smoke automatizado:** `python -m scripts.smoke_integracao`

---

## Pré-requisitos

- [ ] `.env` na raiz e `Sistema de Chamados TI/backend/.env` com o **mesmo** `DATABASE_URL`
- [ ] PostgreSQL acessível (`python -m scripts.verificar_banco`)
- [ ] Usuário de teste em `usuarios_app` (ex.: admin criado com `python -m scripts.criar_admin`)
- [ ] Serviços respondendo (smoke ou manual): 8000, 3000, 8501

---

## 1. Onboarding (Chamados → linha)

**App:** Chamados (`/onboarding?ticket_id=<id>`)

| # | Passo | Esperado |
|---|--------|----------|
| 1 | Login no Chamados | Dashboard carrega |
| 2 | Abrir onboarding com `ticket_id` de chamado aberto | Página carrega sem erro |
| 3 | Buscar linha VAGO pelo número | Card da linha exibido |
| 4 | Clicar **Editar linha no Gerenciamento** | Nova aba Streamlit com banner de contexto |
| 5 | No Streamlit: banner mostra chamado + linha | Filtros aplicados (busca/segmento) |
| 6 | **Voltar para o chamado** | Abre `/tickets?ticket_id=<id>` no Chamados |
| 7 | Concluir onboarding no Chamados | Linha atribuída; registro em `auditoria` com `chamado_id` |

**E2E automatizado:** `python -m scripts.test_auditoria_b3_e2e <senha>`

---

## 2. Manutenção de aparelho

**App:** Chamados (`/manutencao-aparelho?ticket_id=<id>`)

| # | Passo | Esperado |
|---|--------|----------|
| 1 | Buscar linha do colaborador | Dados da linha carregam |
| 2 | **Editar linha no Gerenciamento** | Streamlit com contexto |
| 3 | Registrar manutenção no Chamados | Chamado atualizado; auditoria com `manutencao_aparelho` |

---

## 3. Roubo / perda de linha

**App:** Chamados (`/roubo-perda?ticket_id=<id>`)

| # | Passo | Esperado |
|---|--------|----------|
| 1 | Buscar linha afetada | Linha encontrada |
| 2 | Link **Editar linha no Gerenciamento** (se visível) | Contexto no Streamlit |
| 3 | Registrar roubo/perda | Linha marcada; auditoria com `roubo_perda_linha` |

---

## 4. Transferência de equipe

**App:** Chamados (`/transferencia-equipe?ticket_id=<id>`)

| # | Passo | Esperado |
|---|--------|----------|
| 1 | Buscar linha | Dados corretos |
| 2 | Executar transferência | Equipe/setor atualizados; auditoria `transferencia_equipe` |

---

## 5. Desligamento

**App:** Chamados (`/desligamento?ticket_id=<id>`) ou ticket tipo offboarding

| # | Passo | Esperado |
|---|--------|----------|
| 1 | Fluxo de desligamento com linha vinculada | Nome/código → VAGO |
| 2 | Histórico admin (Streamlit) | Ação `desligamento_linha` com `chamado_id` |

---

## 6. Edição manual (Gerenciamento)

**App:** Streamlit (consulta/edição em massa)

| # | Passo | Esperado |
|---|--------|----------|
| 1 | Login no Gerenciamento | Painel de linhas |
| 2 | Editar linha **sem** contexto de chamado | Auditoria gravada; `chamado_id` vazio ou legado |
| 3 | Abrir Streamlit via link do Chamados **com** `ticket_id` | Banner de contexto; auditoria com `chamado_id` do ticket |
| 4 | Admin → histórico de auditoria | Diff legível (antes → depois) |

---

## 7. Navegação bidirecional (B2)

| # | Passo | Esperado |
|---|--------|----------|
| 1 | Chamados → **Editar linha no Gerenciamento** | URL Streamlit com `ticket_id`, `linha`, `return_url` |
| 2 | Streamlit → **Voltar para o chamado** | `/tickets?ticket_id=<id>` |
| 3 | Streamlit logado → **📌 Chamados** | SSO abre Chamados (redirect se sessão nova) |
| 4 | Deep link `/tickets?ticket_id=<id>` | Lista filtra/mostra o chamado (sem erro React) |

**E2E automatizado (API):** `python -m scripts.test_navegacao_b2_e2e <senha>`

---

## 8. Login e SSO

| # | Passo | Esperado |
|---|--------|----------|
| 1 | Mesmo usuário/senha nos dois apps | Login OK em ambos |
| 2 | Streamlit → 📌 Chamados (sem sessão React) | SSO loga e redireciona |
| 3 | Streamlit → 📌 Chamados (já logado no React) | Abre Chamados autenticado |

---

## Regressões conhecidas a observar

- Página `/tickets?ticket_id=` não pode quebrar (imports React).
- `return_url` deve apontar para `localhost:3000` em dev (variável `CHAMADOS_APP_URL`).
- Referência legada `chamados` vs `tickets`: banner pode avisar — preferir tickets do React.

---

*Fase B4 — maio/2026*
