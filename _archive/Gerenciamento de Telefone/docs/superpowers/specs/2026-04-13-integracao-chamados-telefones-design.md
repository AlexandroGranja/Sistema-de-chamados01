# Design: Integração Ciclo de Vida de Linhas Telefônicas entre Chamados e Gerenciamento

**Data:** 2026-04-13
**Sistemas envolvidos:** Sistema de Chamados TI (FastAPI + React) · Gerenciamento de Telefones (Streamlit)
**Status:** Aprovado para implementação

---

## Contexto

A empresa possui alta rotatividade de vendedores. Dois sistemas gerenciam aspectos diferentes dessas pessoas:

- **Sistema de Chamados TI** — sistema principal de operações de TI (tickets, desligamentos, ativos)
- **Gerenciamento de Telefones** — painel de controle de linhas telefônicas e aparelhos por equipe

Os dois sistemas já compartilham o mesmo banco PostgreSQL e já possuem login unificado via `usuarios_app`. O objetivo deste design é fechar a lacuna operacional: hoje, qualquer evento no ciclo de vida de um colaborador exige atualização manual nos dois sistemas. Após a implementação, o **Chamados é o sistema principal de entrada** e o Gerenciamento é atualizado automaticamente.

---

## Arquitetura

### Abordagem: Integração direta no banco compartilhado (Opção A)

```
┌─────────────────────────────────────────┐
│         PostgreSQL compartilhado        │
│                                         │
│  usuarios_app  │  linhas  │  auditoria  │
└────────────────┼──────────┼─────────────┘
                 │          │
    ┌────────────┘          └──────────────┐
    │                                      │
┌───▼────────────────┐     ┌───────────────▼──────┐
│  Sistema de        │     │  Gerenciamento de    │
│  Chamados TI       │────▶│  Telefones           │
│  (FastAPI + React) │     │  (Streamlit)         │
│                    │     │                      │
│  Entrada de todos  │     │  Painel de status    │
│  os eventos        │     │  (lê e exibe)        │
└────────────────────┘     └──────────────────────┘
```

**Princípios:**
- O Chamados escreve na tabela `linhas` via PostgreSQL compartilhado
- O Gerenciamento de Telefones não muda — reflete o estado atual automaticamente
- Toda alteração é registrada na tabela `auditoria` do Gerenciamento
- Nenhuma nova infraestrutura necessária

### Lookup padrão (todos os fluxos)

Todos os 5 fluxos usam a mesma lógica de busca de linha:
1. Busca por `codigo` (matrícula) — prioridade
2. Fallback: busca por `nome` (normalizado, sem acento, case-insensitive)
3. Exibe prévia da linha encontrada antes de qualquer alteração
4. Técnico confirma → sistema aplica as mudanças e registra auditoria

---

## Os 5 Fluxos

### Fluxo 1 — Desligamento

**Trigger:** Técnico processa o desligamento de um colaborador no Chamados.

**Campos LIMPOS na tabela `linhas`:**

| Campo | Valor após desligamento |
|---|---|
| `nome` | `"VAGO"` |
| `nome_guerra` | `""` |
| `email` | `""` |
| `cargo` | `""` |
| `setor` | `""` |
| `perfil` | `""` |
| `desconto` | `""` |

**Campos PRESERVADOS (pertencem ao aparelho/linha):**

| Campo | Motivo |
|---|---|
| `linha` | Número da operadora |
| `imei_a` / `imei_b` | Controle do aparelho físico |
| `marca` / `modelo` / `aparelho` | Patrimônio da empresa |
| `numero_serie` / `patrimonio` | Auditoria de ativo |
| `chip` / `operadora` | Contrato da linha |
| `equipe` / `gerenciamento` | A linha continua na equipe |
| `ativo` | A linha continua ativa (só está vaga) |

**Interface no Chamados:**
```
┌─────────────────────────────────────────────────┐
│  DESLIGAMENTO — Dados do Colaborador            │
│                                                 │
│  Nome completo: [__________________________]    │
│  Código:        [________]                      │
│                                                 │
│  [ Buscar linha ]                               │
├─────────────────────────────────────────────────┤
│  LINHA ENCONTRADA                        ✓      │
│                                                 │
│  Colaborador:  João Silva                       │
│  Linha:        21 99999-0000                    │
│  Aparelho:     Samsung Galaxy A54               │
│  Equipe:       Consumo Oeste                    │
│                                                 │
│  ☑ Liberar linha ao confirmar desligamento      │
└─────────────────────────────────────────────────┘
```

- Se linha não encontrada: aviso discreto, desligamento prossegue normalmente
- O checkbox vem marcado por padrão quando linha é encontrada
- Integração com Snipe-IT (checkin de ativos) continua inalterada

---

### Fluxo 2 — Onboarding (novo colaborador)

**Trigger:** Técnico recebe email de admissão e abre ticket de onboarding no Chamados.

**Formulário baseado no email de admissão:**

| Campo do email | Campo no sistema |
|---|---|
| NOME | `nome` |
| MATRÍCULA | `codigo` |
| CARGO | `cargo` |
| EMPRESA | `empresa` |
| GESTOR | `gestor` |
| SETOR | `setor` |
| SUBSTITUIÇÃO | campo auxiliar para sugestão de linha |

**Campos PREENCHIDOS na tabela `linhas`:**
`nome`, `nome_guerra`, `codigo`, `cargo`, `setor`, `empresa`, `equipe`, `gestor`, `email`

**Campos PRESERVADOS (aparelho já existe na linha):**
`linha`, `imei_a`, `imei_b`, `marca`, `modelo`, `aparelho`, `chip`, `operadora`, `numero_serie`, `patrimonio`

**Lógica de sugestão de linha:**
- Técnico informa o número da linha manualmente (já sabe de cabeça)
- Se campo "SUBSTITUIÇÃO" estiver preenchido, o sistema busca a linha do colaborador substituído e exibe sugestão: *"Linha de Daniel (21 99999-0000) está VAGO — usar essa?"*
- Técnico pode aceitar a sugestão ou informar outro número

---

### Fluxo 3 — Manutenção / Troca de Aparelho

**Trigger:** Aparelho do colaborador vai para conserto; técnico coloca aparelho reserva.

**Campos ALTERADOS na tabela `linhas`:**

| Campo | Atualizado com |
|---|---|
| `imei_a` | IMEI do aparelho reserva |
| `imei_b` | IMEI B do aparelho reserva (se aplicável) |
| `marca` | Marca do aparelho reserva |
| `modelo` | Modelo do aparelho reserva |
| `aparelho` | Nome/descrição do aparelho reserva |
| `numero_serie` | Número de série do reserva |
| `patrimonio` | Patrimônio do reserva |
| `chip` | Chip do reserva (se houver troca) |

**Campos PRESERVADOS (pertencem ao colaborador/linha):**
Todos os campos pessoais e de equipe — `nome`, `email`, `cargo`, `setor`, `equipe`, `linha`, etc.

**Nota:** Quando a manutenção ocorre no contexto de um desligamento, o fluxo de desligamento já cobre tudo — não há troca de aparelho, a linha vira VAGO e o aparelho vai para conserto como está.

---

### Fluxo 4 — Roubo e Perda

**Trigger:** Colaborador teve aparelho roubado ou perdido; técnico registra no Chamados.

**Cenário A — Mesma linha, aparelho novo:**

| Campo | Atualizado com |
|---|---|
| `imei_a` / `imei_b` | IMEI do aparelho substituto |
| `marca` / `modelo` / `aparelho` | Dados do novo aparelho |
| `chip` | Novo chip (se aplicável) |
| `numero_serie` / `patrimonio` | Dados do novo aparelho |

Campos pessoais e `linha` preservados.

**Cenário B — Linha nova + aparelho reserva:**

Todos os campos do Cenário A + atualização do campo `linha` com o novo número.
Campos pessoais (`nome`, `codigo`, `email`, `setor`, `cargo`, `equipe`) preservados.

**Interface:** O técnico seleciona o cenário (A ou B) na tela do chamado antes de confirmar.

---

### Fluxo 5 — Transferência entre Equipes

**Trigger:** Colaborador muda de equipe/setor, com ou sem promoção.

**Campos ALTERADOS:**

| Campo | Condição |
|---|---|
| `equipe` | Sempre |
| `setor` | Sempre |
| `gestor` | Sempre |
| `cargo` | Somente se for promoção (checkbox "É promoção?") |
| `empresa` | Opcional (campo habilitado, raramente usado) |

**Campos PRESERVADOS:** Todos os dados do aparelho e linha, `nome`, `codigo`, `email`.

---

## Auditoria

Todos os 5 fluxos registram na tabela `auditoria` do Gerenciamento:

| Campo | Valor |
|---|---|
| `acao` | `"desligamento"` / `"onboarding"` / `"manutencao"` / `"roubo_perda"` / `"transferencia"` |
| `usuario_responsavel` | Username do técnico no Chamados |
| `chamado_id` | ID do chamado de origem |
| `descricao` | Resumo da alteração (campos modificados) |
| `data_hora` | Timestamp UTC |

---

## Componentes a implementar

### Backend — Sistema de Chamados (FastAPI)

1. **Serviço `telefones_service.py`** — camada de acesso à tabela `linhas`:
   - `buscar_linha(db, codigo, nome)` → retorna linha encontrada para prévia
   - `liberar_linha(db, linha_id, tecnico, chamado_id)` → desligamento
   - `atribuir_linha(db, linha_id, dados_colaborador, chamado_id)` → onboarding
   - `atualizar_aparelho(db, linha_id, dados_aparelho, chamado_id)` → manutenção / roubo
   - `transferir_linha(db, linha_id, dados_equipe, chamado_id)` → transferência
   - `registrar_auditoria(db, acao, linha_id, tecnico, chamado_id, descricao)`

2. **Novos endpoints em `/api/telefones/`:**
   - `GET /buscar-linha?codigo=X&nome=Y` — lookup para prévia
   - `POST /liberar-linha` — desligamento
   - `POST /atribuir-linha` — onboarding
   - `POST /atualizar-aparelho` — manutenção / roubo e perda
   - `POST /transferir` — transferência

### Frontend — Sistema de Chamados (React)

Nova seção **"Linha Telefônica"** presente em todos os fluxos relevantes:
- Campo de busca (código + nome)
- Card de prévia da linha encontrada
- Formulário específico de cada fluxo
- Feedback de sucesso/erro após confirmação

---

## O que NÃO muda

- Login unificado via `usuarios_app` — já funciona
- SSO entre os sistemas — já funciona
- Integração com Snipe-IT no desligamento — continua igual
- Interface do Gerenciamento de Telefones — nenhuma alteração
- Fluxo de chamados existentes — nenhuma alteração

---

## Fora do escopo deste design

- Sincronização reversa (Gerenciamento → Chamados)
- Notificações automáticas por email/WhatsApp
- Dashboard unificado com métricas dos dois sistemas
