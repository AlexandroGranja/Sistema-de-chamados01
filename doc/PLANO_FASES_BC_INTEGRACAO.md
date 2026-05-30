# Plano detalhado — Fases B e C (Integração e Unificação)

> **Pré-requisito:** Fase A concluída (monorepo organizado, ativador corrigido, docs centralizadas, `.env` padronizado).
>
> **Objetivo geral:** um fluxo operacional claro, um ID de chamado confiável, auditoria completa e, opcionalmente, uma interface única.

---

## Estado após Fase A

| Item | Status |
|------|--------|
| App oficial Streamlit na raiz | OK |
| Chamados em `Sistema de Chamados TI/` | OK |
| Cópia duplicada | Arquivada em `_archive/` |
| `ativador_completo.bat` | Aponta para paths dentro do repo |
| Documentação | Índice em `doc/README.md` |
| `.env` | Mesmo `DATABASE_URL` raiz + backend |

**Dívida técnica que B/C resolvem:**

1. Duas tabelas de chamado: `chamados` (Streamlit) vs `tickets` (React).
2. Duas camadas escrevem em `linhas` sem contrato único de regras.
3. Navegação entre apps ainda manual (URL/SSO parcial).
4. Auditoria nem sempre amarra `tickets.id` quando a ação veio do React.

---

## Fase B — Integração operacional

**Meta:** operador trabalha nos dois apps sem ambiguidade; todo evento de linha rastreável ao ticket correto.

**Duração estimada:** 3–5 semanas (incremental, entregas por sprint).

### B1 — ID único de chamado (`tickets.id` como fonte da verdade)

**Problema:** URL `?chamado_id=123` no Streamlit pode referir `chamados.id` ou `tickets.id`.

**Entregas:**

1. Documentar convenção: **`chamado_id` na auditoria = `tickets.id`** (React).
2. No Streamlit (`app.py` + `repository.py`):
   - Aceitar `ticket_id` como parâmetro preferencial; manter `chamado_id` como alias.
   - Ao receber ID, validar existência em `tickets` (via SQL leve ou view).
   - Se não existir em `tickets`, tentar `chamados` (legado) com aviso na UI.
3. Criar view SQL opcional `v_chamado_unificado` unindo metadados mínimos de `tickets` + `chamados` para consulta.

**Arquivos:**

- `src/db/repository.py` — `resolver_chamado_id()`, `validar_ticket_id()`
- `src/db/schema_postgres.sql` — view + comentários
- `app.py` — banner “Atuando no chamado #123 (tickets)”

**Critério de aceite:**

- Abrir `http://localhost:8501/?ticket_id=42` vincula auditoria a `tickets.id=42`.
- Histórico admin mostra link clicável para chamado no React.

---

### B2 — Navegação bidirecional (SSO + deep links)

**Entregas:**

1. **Chamados → Gerenciamento**
   - Botão “Editar linha no Gerenciamento” nas páginas: Onboarding, Manutenção, Roubo, Transferência, Desligamento.
   - URL gerada: `{streamlit_base}/?ticket_id={id}&linha={numero}&segmento_chamado=...&return_url={frontend}/tickets/{id}`
2. **Gerenciamento → Chamados**
   - Sidebar: “Abrir Sistema de Chamados” usando SSO existente (`criar_sso_code` + `CHAMADOS_APP_URL`).
   - Se houver `ticket_id` em sessão, abrir direto o ticket no React.
3. Config central:
   - Raiz `.env`: `CHAMADOS_APP_URL`, `STREAMLIT_APP_URL` (novo, para o backend gerar links).
   - Backend `config.py`: ler `STREAMLIT_APP_URL`.

**Arquivos:**

- `app.py` — botão SSO + retorno
- `Sistema de Chamados TI/frontend/src/pages/*.jsx` — links para Streamlit
- `Sistema de Chamados TI/backend/app/core/config.py`
- `Sistema de Chamados TI/backend/app/api/v1/endpoints/telefones.py` — helper de URL

**Critério de aceite:**

- Operador no ticket de onboarding clica e cai no Streamlit já filtrado na linha, com banner de contexto.
- Após salvar no Streamlit, botão “Voltar ao chamado” usa `return_url`.

---

### B3 — Auditoria unificada para ações via API

**Problema:** FastAPI altera `linhas` em `services/telefones.py`; Streamlit grava `auditoria` em `repository.py`. Nem toda mutação API gera registro equivalente.

**Entregas:**

1. Extrair função compartilhada (Python) ou procedimento SQL para `registrar_auditoria_linha`:
   - `usuario`, `acao`, `tabela`, `registro_id`, `campo`, `valor_anterior`, `valor_novo`, `chamado_id` (= `ticket_id`).
2. Chamar em **todos** os endpoints `/api/telefones/*` após commit bem-sucedido.
3. Chamados de desligamento (`sync_offboarding_to_telefones`) já auditados com `ticket_id`.

**Arquivos:**

- `Sistema de Chamados TI/backend/app/services/telefones.py`
- `Sistema de Chamados TI/backend/app/services/auditoria.py` (novo, espelhando lógica do Streamlit)
- `src/db/repository.py` — alinhar formato de mensagens

**Critério de aceite:**

- Onboarding via React aparece no histórico do Streamlit (admin) com `chamado_id` correto.
- Campos alterados listados no mesmo formato “antes → depois”.

---

### B4 — Matriz operacional (documentação viva)

**Entregas:**

1. Tabela “qual app usar” em `doc/README.md` (já iniciada) + fluxograma Mermaid.
2. Checklist de QA por fluxo: onboarding, manutenção, roubo, transferência, desligamento, edição manual.
3. Script de smoke test opcional: `scripts/smoke_integracao.py` (health 8000, 8501, query `linhas` count).

**Critério de aceite:**

- Novo operador consegue decidir app correto sem perguntar ao dev.

---

### B5 — Sincronização de usuários estável

**Entregas:**

1. Documentar e automatizar `sync_users_from_usuarios_app.py` pós-criação de admin no Streamlit.
2. Admin Streamlit: aviso se usuário existe em `usuarios_app` mas não em `users`.
3. Política de senha documentada (duas senhas possíveis hoje — ver `BANCO_UNIFICADO.md`).

---

### Ordem de implementação Fase B

```text
B1 (ID único) → B3 (auditoria API) → B2 (navegação) → B4 (docs QA) → B5 (usuários)
```

B1 e B3 são bloqueantes para confiança operacional; B2 melhora UX.

---

## Fase C — Unificação (longo prazo)

**Meta:** reduzir duplicidade de UI e regras; backend como única camada de escrita (alinhado a `ARQUITETURA_SISTEMA_UNIFICADO.md`).

**Duração estimada:** 2–4 meses (depende se mantém Streamlit para admin).

### C1 — Camada de serviço única para `linhas`

**Entregas:**

1. Mover regras de negócio de `repository.py` e `telefones.py` para módulo compartilhado ou expandir FastAPI como **API interna** do monorepo.
2. Streamlit passa a chamar API (HTTP local) em vez de SQL direto — feature flag `USE_TELEFONES_API=true`.
3. Regras centralizadas: linha vaga, conflito de edição, validações de segmento/equipe.

**Risco:** regressão em edição em massa. Mitigação: flag + testes manuais por segmento.

---

### C2 — Modelo único de chamado

**Entregas:**

1. Deprecar tabela `chamados` / UI Streamlit `_render_chamados_content()` (substituída pelo React).
2. Migrar registros legados `chamados` → `tickets` (script one-shot) ou manter `chamados` somente leitura.
3. FK `auditoria.chamado_id` documentada como `tickets.id` (sem ambiguidade).

---

### C3 — Interface única (decisão de produto)

**Opção A — React principal + Streamlit admin-only**

- Operadores usam só Chamados + telas de linha embutidas (já existem).
- Streamlit restrito a admin (config, importações, histórico bruto).

**Opção B — React absorve Gerenciamento**

- Reimplementar grid de linhas, filtros e edição em massa no frontend.
- Desativar Streamlit após paridade.

**Opção C — Manter dual UI indefinidamente**

- Aceitável se B1–B3 estiverem sólidos; custo de manutenção maior.

**Recomendação:** Opção A como passo intermediário; avaliar B após 3 meses de uso.

---

### C4 — Identidade SSO real (Keycloak / Azure AD)

**Entregas:**

1. PoC Keycloak (já esboçado em docs históricos `_archive/`).
2. Substituir SSO por código temporário por OIDC nos dois apps.
3. Logout global.

Referência arquivada: `_archive/Gerenciamento de Telefone/docs/superpowers/plans/2026-04-29-keycloak-sso.md`

---

### C5 — Deploy e observabilidade unificados

**Entregas:**

1. `docker-compose.yml` na raiz: postgres + backend + frontend + streamlit (opcional).
2. Nginx reverse proxy: `/chamados`, `/telefones`, `/api`.
3. Backup automatizado Postgres; healthchecks.

---

### Ordem de implementação Fase C

```text
C1 (API única) → C2 (modelo chamado) → C3 (UI) → C4 (SSO) → C5 (deploy)
```

---

## Riscos e mitigações

| Risco | Impacto | Mitigação |
|-------|---------|-----------|
| IDs de chamado inconsistentes | Auditoria incorreta | B1 antes de qualquer outra entrega |
| Edição concorrente Streamlit + API | Sobrescrita | Manter detecção de conflito; C1 centraliza |
| Duas senhas por usuário | Login confuso | B5 + comunicação + convergir hash |
| Remover Streamlit cedo demais | Perda de produtividade admin | Opção A em C3 |

---

## Métricas de sucesso

| Métrica | Fase B | Fase C |
|---------|--------|--------|
| % alterações de linha com `ticket_id` na auditoria | > 95% fluxos chamados | 100% |
| Tempo para ir chamado → linha → voltar | < 30 s (1 clique) | < 15 s |
| Incidentes “salvou no app errado” | zero recorrentes | — |
| Pontos de escrita em `linhas` | 2 (aceito) | 1 (API) |

---

## Próximo passo recomendado

Iniciar **B1** (ID único `tickets.id`) — menor risco, maior clareza imediata para auditoria e links.

---

*Documento criado na Fase A — maio/2026. Ver também [[doc/README.md]] e [[doc/ARQUITETURA_SISTEMA_UNIFICADO.md]].*
