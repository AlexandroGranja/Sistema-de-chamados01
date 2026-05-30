# Textos prontos — LinkedIn e currículo

Copie e adapte. Substitua `[URL]` pelo link do repositório GitHub.

---

## LinkedIn — post de lançamento

**Título sugerido:** Integração Chamados + Telefonia corporativa

Desenvolvi um monorepo full-stack que unifica **Sistema de Chamados TI** (React + FastAPI) com **gerenciamento de linhas telefônicas** (Streamlit admin) sobre **PostgreSQL compartilhado**.

Destaques técnicos:
• Fluxo operador: ticket de telefonia → API atualiza linha → auditoria com `ticket_id`  
• Deep links + SSO entre React e Streamlit  
• Consolidação de tickets (legado → modelo único)  
• Scripts E2E e smoke test de integração  
• Dados demo anonimizados para repositório público  

Stack: React, FastAPI, Streamlit, PostgreSQL, Docker Compose.

Repo: [URL]  
Demo local em ~2 min com `ativador_completo.bat`.

#FullStack #Python #React #FastAPI #PostgreSQL #Portfolio

---

## LinkedIn — seção Projetos (bullets)

**Sistema de Chamados TI + Telefonia Corporativa** · Projeto pessoal · [URL]

- Arquitetura monorepo com React (Chamados), FastAPI e Streamlit (admin linhas) sobre PostgreSQL unificado  
- Implementei integração REST `/api/telefones`, SSO entre apps e auditoria com rastreio por `ticket_id`  
- Migrei modelo legado de chamados para `tickets` como fonte da verdade  
- Cobertura de integração com testes E2E (navegação B2, auditoria B3, flags C1–C4)  
- Ambiente reproduzível: ativador Windows + Docker Compose stack  

---

## Currículo — bullet único (compacto)

**Sistema de Chamados TI + Telefonia** — React, FastAPI, Streamlit, PostgreSQL · Projeto pessoal: plataforma integrada de tickets e linhas móveis com auditoria unificada, SSO/deep links entre frontends e testes E2E de integração; dados demo anonimizados.

---

## Currículo — 3 bullets (detalhado)

- Projetou e implementou monorepo full-stack (React + FastAPI + Streamlit) com banco PostgreSQL compartilhado para chamados de TI e ciclo de vida de linhas telefônicas  
- Entregou integração operacional: API de linhas, deep links bidirecionais, auditoria correlacionada a `ticket_id`, sync de usuários e modo admin-only no Streamlit  
- Validou fluxos críticos com scripts smoke/E2E e documentou arquitetura para portfólio (case study, README, anonimização de dados sensíveis)  

---

## Entrevista — pitch de 30 segundos

"Construí uma plataforma onde o operador de TI resolve chamados de telefonia só pelo React. Quando a linha precisa de edição manual, um deep link abre o painel admin em Streamlit já com o contexto do ticket. Toda mutação passa pela API e grava auditoria no mesmo PostgreSQL. É um projeto pessoal com dados fictícios, mas a arquitetura espelha o que você veria em integração entre sistemas legados e um produto principal moderno."

---

## Skills tags (ATS)

React · TypeScript · Python · FastAPI · Streamlit · PostgreSQL · SQLAlchemy · REST API · JWT · SSO · Docker · Integração de sistemas · Auditoria · E2E testing
