# Papeis de UI — Fase C3 (Opcao A)

> **Decisao:** React (Chamados) = app operacional; Streamlit = admin + edicao pontual via ticket.

---

## Quem usa o que

| Perfil | App principal | Streamlit |
|--------|---------------|-----------|
| Operador | **Chamados** (React) | So quando abrir linha a partir de um ticket (deep link B2) |
| Administrador | Chamados + Streamlit | Painel completo, config, usuarios, auditoria bruta |

---

## Modos de acesso ao Streamlit

Controlado por `STREAMLIT_ADMIN_ONLY` (padrao `true`).

| Modo | Quem | O que ve |
|------|------|----------|
| `admin_full` | Admin ou `STREAMLIT_ADMIN_ONLY=false` | Painel + Config + Adicionar linha |
| `operador_chamado` | Operador com `ticket_id` / linha na URL | Grid filtrado + banner de contexto + voltar ao chamado |
| `blocked_panel` | Operador sem contexto | Tela de redirecionamento para o React |
| `blocked_config` | Operador em `?pagina=config` | Aviso + volta ao painel |

---

## Deep link operacional (B2 + C3)

URL tipica vinda do Chamados:

```text
http://localhost:8501/?ticket_id=42&linha=21999990000&return_url=http://localhost:3000/tickets?ticket_id=42
```

Operador autenticado edita a linha e usa **Voltar para o chamado**.

---

## Variavel de ambiente

```env
# Fase C3 — true = operador sem contexto nao ve o grid (padrao)
STREAMLIT_ADMIN_ONLY=true
```

Para desenvolvimento com dual-UI antiga: `STREAMLIT_ADMIN_ONLY=false`.

---

## Teste

```powershell
python -m scripts.test_c3_streamlit_access
```

---

*Fase C3 — maio/2026. Ver [[doc/PLANO_FASES_BC_INTEGRACAO.md]].*
