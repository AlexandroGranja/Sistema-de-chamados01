# Frontend Redesign — Sistema de Chamados TI (Prosper)

## Objetivo

Redesenhar o frontend do Sistema de Chamados TI para transmitir identidade corporativa profissional, eliminando a aparência genérica atual. O redesign acompanha a paleta da logo Prosper (preto + dourado), introduz sidebar lateral fixa e suporte a modo claro/escuro.

## Contexto

- **Sistema:** Sistema de Chamados TI — FastAPI + React + Material UI
- **Localização:** `C:\Users\TI02\Desktop\Sistema de Chamados TI\frontend\`
- **Brand:** Prosper, logo em `frontend/assets/logo.png` (oval preta + círculo dourado com "P")
- **Paleta da logo:** Preto `#111827` + Dourado `#f2c230`
- **Problema atual:** Layout horizontal genérico, uso fraco do dourado, hierarquia visual fraca, densidade sem peso visual adequado

---

## Arquitetura

### Estrutura de Layout

Substituir o AppBar horizontal por uma **sidebar lateral fixa de 240px**. A área de conteúdo ocupa o espaço restante (`flex: 1`, `overflow-y: auto`). Sem AppBar no topo — a sidebar é a única navegação.

```
┌──────────────┬────────────────────────────────────┐
│   SIDEBAR    │         CONTENT AREA               │
│   240px      │         flex-1                     │
│   fixa       │         overflow-y: auto           │
│              │                                    │
│  [Logo]      │  ┌─ Page Header ──────────────┐   │
│              │  │  Título da página           │   │
│  Dashboard   │  └─────────────────────────────┘   │
│  Chamados    │                                    │
│  Telefonia ▾ │  ┌─ Content ───────────────────┐   │
│   Onboarding │  │                             │   │
│   Manutenção │  │                             │   │
│   Roubo/Perda│  └─────────────────────────────┘   │
│   Transf.    │                                    │
│  ─────────── │                                    │
│  [Avatar]    │                                    │
│  Nome user   │                                    │
│  [☀/🌙]     │                                    │
└──────────────┴────────────────────────────────────┘
```

**Sidebar:**
- Largura fixa 240px, sem collapse
- Logo Prosper no topo (padding 24px)
- Itens de menu: ícone + label, `border-left: 3px solid #f2c230` no ativo
- Telefonia: submenu expansível inline (sem dropdown flutuante)
- Rodapé fixo: avatar + nome do usuário + toggle claro/escuro

---

## Sistema de Cores

### Tokens por Modo

| Token | Modo Claro | Modo Escuro |
|---|---|---|
| `sidebar bg` | #111827 | #0d1117 |
| `gold accent` | #f2c230 | #f2c230 |
| `gold hover` | #d4a820 | #d4a820 |
| `bg default` | #f9fafb | #111827 |
| `bg paper` | #ffffff | #1f2937 |
| `bg subtle` | #f3f4f6 | #374151 |
| `text primary` | #111827 | #f9fafb |
| `text secondary` | #6b7280 | #9ca3af |
| `border` | #e5e7eb | #374151 |

### Cores Funcionais (Status)

| Status | Cor | Badge background |
|---|---|---|
| Aberto | #3b82f6 | #eff6ff |
| Em andamento | #f59e0b | #fffbeb |
| Fechado | #10b981 | #ecfdf5 |
| Urgente | #ef4444 | #fef2f2 |

### Regra de Uso do Dourado

O dourado aparece **apenas como accent pontual**, nunca como background de área grande:
- Botão primário (bg dourado, texto preto)
- Item ativo na sidebar (border-left 3px)
- Ícones de métrica no Dashboard
- Focus de campo de formulário (outline dourado)

---

## Tipografia

Fonte: **Inter** (via MUI)

| Elemento | Tamanho | Peso |
|---|---|---|
| Page title | 22px | 700 |
| Section title | 16px | 600 |
| Body | 14px | 400 |
| Caption | 12px | 400 |
| Metric number | 32px | 700 |

---

## Componentes

### Cards de Métrica (Dashboard)
- `border-left: 3px solid #f2c230`
- Número grande (32px 700) + label + caption "↑ N hoje"
- Ícone MUI em dourado no canto superior

### Badges de Status (`StatusBadge.jsx` — novo componente)
- Pill arredondado (`border-radius: 12px`)
- Fundo colorido suave + texto sólido (cores funcionais acima)
- Ponto colorido (`●`) antes do texto
- Reutilizado em tabelas e detalhes de chamado

### Botão Primário
- Background: `#f2c230`, texto: `#111827`, peso 600
- Hover: `#d4a820`
- Border-radius: 6px
- Sem sombra elevada

### Tabela de Chamados
- Header: `bg.subtle`, texto uppercase 11px `text.secondary`
- Rows: hover sutil, apenas linhas horizontais (sem bordas verticais)
- Badge de status inline

### Formulários
- Variant `outlined`, border `#e5e7eb`
- Focus: `outline: 2px solid #f2c230`
- Labels acima dos campos

---

## Modo Claro / Escuro

- Controlado via `useState` em `App.jsx` (ou `ThemeContext`)
- Preferência persistida em `localStorage` com chave `prosper-color-mode`
- Toggle: ícone `LightModeIcon` / `DarkModeIcon` no rodapé da sidebar
- MUI `ThemeProvider` recebe `mode: 'light' | 'dark'` dinamicamente

---

## Escopo de Arquivos

### Criar
- `frontend/src/theme.js` — tokens de cor, tipografia Inter, modo dual
- `frontend/src/components/StatusBadge.jsx` — badge reutilizável de status

### Redesenhar completamente
- `frontend/src/components/Layout.jsx` — AppBar → Sidebar lateral

### Ajustes visuais (sem mudança de lógica)
- `frontend/src/App.jsx` — integrar ThemeProvider com modo dual
- `frontend/src/pages/Login.jsx` — card centralizado, fundo escuro, focus dourado
- `frontend/src/pages/Dashboard.jsx` — metric cards com border dourada, tabela com badges
- `frontend/src/pages/Chamados.jsx` — tabela com StatusBadge, filtros no topo
- `frontend/src/pages/AbrirChamado.jsx` — formulário com seções e focus dourado
- `frontend/src/pages/Desligamento.jsx` — idem AbrirChamado
- `frontend/src/pages/Onboarding.jsx` — formulário consistente
- `frontend/src/pages/ManutencaoAparelho.jsx` — formulário consistente
- `frontend/src/pages/RouboPerdaLinha.jsx` — formulário consistente
- `frontend/src/pages/TransferenciaEquipe.jsx` — formulário consistente

### O que NÃO muda
- Lógica de negócio, estados React, chamadas de API
- Estrutura de rotas
- Backend

---

## Critérios de Sucesso

1. Sidebar lateral fixa visível em todas as páginas autenticadas
2. Toggle claro/escuro funcional, preferência persistida
3. Dourado visível como accent sem dominar backgrounds
4. StatusBadge usado consistentemente em todas as ocorrências de status
5. Fonte Inter aplicada globalmente
6. Dashboard com metric cards no novo padrão visual
