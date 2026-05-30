# Checklist de screenshots — portfólio

Capture em **1920×1080** (ou 1440×900). Oculte barra de endereço se preferir; use dados demo (`admin_demo`).

Salvar sugerido: `doc/screenshots/` (pasta local, não versionada — adicionar ao `.gitignore` se quiser).

---

## Cena 1 — Dashboard Chamados (React)

**URL:** http://localhost:3000  
**Login:** `admin_demo` / `Demo@2026!`

**Mostrar:**
- Sidebar + lista ou dashboard de tickets  
- Pelo menos um ticket aberto (telefonia se possível)  
- Visual escuro/claro consistente  

**Legenda sugerida:** *Dashboard principal — operador gerencia tickets de TI e telefonia.*

---

## Cena 2 — Fluxo telefonia (React)

**Mostrar:**
- Formulário ou detalhe de ticket de onboarding/manutenção  
- Campo de linha ou ação que altera telefone  
- Botão/link **Ver/editar linha** (integração B2)  

**Legenda sugerida:** *Fluxo de telefonia — ticket dispara alteração de linha via API.*

---

## Cena 3 — Auditoria / admin (Streamlit ou histórico)

**Opção A — Streamlit:** http://localhost:8501/?ticket_id=1 (ajuste ID)  
- Grid ou histórico de auditoria com coluna `chamado_id` / ticket  

**Opção B — React:** histórico do ticket mostrando alteração de linha  

**Legenda sugerida:** *Rastreabilidade — toda alteração de linha referencia o ticket.*

---

## Bônus (opcional)

| Cena | Onde | Para quê |
|------|------|----------|
| Deep link URL | Barra de endereço Streamlit | Mostrar `ticket_id`, `return_url` |
| Docker Compose | Terminal `docker compose ps` | Deploy reproduzível |
| Testes E2E | Terminal smoke PASS | Qualidade |

---

## Antes de publicar

- [ ] Rodou `python -m scripts.anonimizar_dados_demo`  
- [ ] Nenhum nome/telefone real visível  
- [ ] `.env` fora do Git  
- [ ] README aponta para login demo  
