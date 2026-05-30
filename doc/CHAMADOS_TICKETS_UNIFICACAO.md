# Unificação chamados legado → tickets (Fase C2)

> **Objetivo:** um único modelo operacional de chamado no React (`tickets`), com rastreabilidade clara na auditoria.

---

## Fonte da verdade

| Conceito | Tabela | Uso |
|----------|--------|-----|
| Chamado operacional (React) | **`tickets`** | Abertura, fluxos de telefonia, comentários, histórico |
| Chamado legado (Streamlit) | **`chamados`** | Somente leitura / histórico; **não criar novos** |
| ID na auditoria | **`auditoria.chamado_id`** | **`tickets.id`** quando a ação veio do fluxo integrado |

A coluna `auditoria.chamado_id` **não tem FK rígida** (Fase B1) para permitir referências legadas durante a transição. Novas gravações devem usar sempre `tickets.id`.

---

## Resolução de URL no Streamlit

Parâmetros aceitos: `ticket_id` (preferencial) ou `chamado_id` (alias).

Ordem em `resolver_referencia_chamado()`:

1. Busca em **`tickets.id`**
2. Se não achar, busca em **`chamados.id`** (legado) — UI exibe aviso
3. **Não** cria mais stub em `chamados` quando a tabela `tickets` existe (Fase C2)

---

## UI Streamlit

- Botão **📌 Chamados** (navbar): abre o React via SSO.
- Página interna `_render_chamados_content()` foi **descontinuada** — use o React.
- Banner “Contexto de chamado” continua ativo ao editar linhas vindas de um ticket.

---

## Scripts operacionais

### Verificar estado

```powershell
python -m scripts.verificar_chamados_legado
```

Mostra contagens de `chamados`, `tickets`, auditoria legada e órfãos.

### Migrar legado (opcional, one-shot)

Converte registros de `chamados` em novos `tickets` com número `LEG-{numero_chamado}`.

```powershell
# Simular
python -m scripts.migrar_chamados_para_tickets --dry-run

# Gravar
python -m scripts.migrar_chamados_para_tickets --yes

# Gravar e remapear auditoria/movimentações para o novo tickets.id
python -m scripts.migrar_chamados_para_tickets --yes --remap-auditoria
```

**Pré-requisitos:**

- `DATABASE_URL` unificado
- Tabela `users` populada (`python -m scripts.sync_usuarios_chamados`)
- Backend Chamados com schema (`alembic upgrade head`)

A tabela `chamados` **não é apagada** — permanece como arquivo histórico.

---

## Mapeamento legado → React

| chamados | tickets |
|----------|---------|
| tipo `incidente` | `incident` |
| tipo `solicitacao` / `gerenciamento` | `request` |
| tipo `manutencao` | `maintenance` |
| status `aberto` | `open` |
| status `em_andamento` | `in_progress` |
| status `aguardando` | `waiting_user` |
| status `resolvido` | `resolved` |
| status `fechado` | `closed` |
| prioridade `baixa`…`critica` | `low`…`critical` |

---

## View unificada (consulta)

`v_chamado_unificado` (PostgreSQL) lista tickets e chamados legados sem colisão de id:

- Origem `tickets` — preferencial
- Origem `chamados` — apenas ids que **não** existem em `tickets`

---

## Critério de aceite C2

- [x] Documentação da convenção `auditoria.chamado_id = tickets.id`
- [x] Script de verificação de legado/órfãos
- [x] Script de migração opcional (dry-run + `--yes`)
- [x] Stub automático em `chamados` desativado com PostgreSQL + `tickets`
- [x] UI legada Streamlit descontinuada (redirect mental via 📌 Chamados)

---

*Fase C2 — maio/2026. Ver [[doc/PLANO_FASES_BC_INTEGRACAO.md]].*
