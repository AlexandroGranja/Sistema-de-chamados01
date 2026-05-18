# Redesign Gerenciamento de Telefones — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended)
> or superpowers:executing-plans. Steps use checkbox (`- [ ]`) syntax.

**Goal:** Redesenhar o Gerenciamento de Telefones com visual Prosper (sidebar dark + gold), colunas limpas, aba admin configurável e autonomia de organização para os usuários.

**Architecture:** Manter Streamlit com `st.data_editor` (edição estilo planilha). Substituir a navbar horizontal por uma sidebar Streamlit estilizada com CSS Prosper (#111827 + #f2c230). Extrair lógica de páginas para módulos em `src/pages/` para reduzir o monólito de 4192 linhas. Adicionar novas tabelas PostgreSQL para equipes, gestores, filtros salvos, preferências de colunas e flags de linha.

**Tech Stack:** Python 3.10+, Streamlit, PostgreSQL (psycopg2), pandas, openpyxl

---

## Mapa de Arquivos

| Ação | Arquivo | Propósito |
|------|---------|-----------|
| Modificar | `app.py` | Remover navbar top, adicionar roteamento via sidebar, reduzir para ~800 linhas |
| Criar | `src/pages/painel.py` | Lógica do painel principal (extraída de app.py) |
| Criar | `src/pages/config_admin.py` | Aba Admin completa (equipes, gestores, regras, usuários) |
| Criar | `src/components/sidebar.py` | Sidebar Prosper: navegação, filtros, preferências |
| Criar | `src/components/editor_linhas.py` | Data editor com show/hide colunas, flags, linha rápida |
| Criar | `src/components/filtros.py` | Filtros salvos: salvar, listar, aplicar |
| Modificar | `src/db/repository.py` | Novas funções: equipes_config, gestores, filtros, prefs, flags |
| Criar | `src/db/migrations.py` | Migrations para novas tabelas |
| Modificar | `src/core/config.py` | Constante NEW_COLUMNS_ORDER |

---

## Novas Tabelas PostgreSQL

```sql
-- Equipes configuráveis (substitui hardcoded)
CREATE TABLE IF NOT EXISTS equipes_config (
    id SERIAL PRIMARY KEY,
    nome VARCHAR(150) NOT NULL,
    segmento VARCHAR(100) NOT NULL,
    gestor VARCHAR(255),
    setor VARCHAR(255),
    ativo BOOLEAN NOT NULL DEFAULT TRUE,
    criado_em TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Gestores/gerência configuráveis (substitui GESTORES_MEDICAMENTO dict)
CREATE TABLE IF NOT EXISTS gestores_config (
    id SERIAL PRIMARY KEY,
    nome VARCHAR(255) NOT NULL,
    equipe VARCHAR(150),
    segmento VARCHAR(100),
    email VARCHAR(255),
    ativo BOOLEAN NOT NULL DEFAULT TRUE
);

-- Filtros salvos por usuário
CREATE TABLE IF NOT EXISTS filtros_salvos (
    id SERIAL PRIMARY KEY,
    usuario_id INTEGER NOT NULL REFERENCES usuarios_app(id) ON DELETE CASCADE,
    nome VARCHAR(100) NOT NULL,
    filtro_json JSONB NOT NULL,
    criado_em TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Preferências de colunas visíveis por usuário
CREATE TABLE IF NOT EXISTS user_column_prefs (
    usuario_id INTEGER PRIMARY KEY REFERENCES usuarios_app(id) ON DELETE CASCADE,
    colunas_visiveis JSONB NOT NULL DEFAULT '[]',
    atualizado_em TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Flags/destaques em linhas
CREATE TABLE IF NOT EXISTS line_flags (
    id SERIAL PRIMARY KEY,
    linha_id BIGINT NOT NULL REFERENCES linhas(id) ON DELETE CASCADE,
    usuario_id INTEGER NOT NULL REFERENCES usuarios_app(id) ON DELETE CASCADE,
    cor VARCHAR(20) NOT NULL DEFAULT 'yellow',
    nota TEXT,
    criado_em TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE(linha_id, usuario_id)
);
```

---

## Task 1: Migrations — Novas Tabelas

**Files:**
- Create: `src/db/migrations.py`
- Modify: `src/db/repository.py` (chamar migrations em `init_db`)

- [ ] **Step 1: Criar `src/db/migrations.py`**

```python
# src/db/migrations.py
"""Migrations para novas tabelas do redesign."""
from __future__ import annotations
import logging
from typing import Any

logger = logging.getLogger(__name__)


def run_migrations(conn: Any) -> None:
    """Executa todas as migrations idempotentes."""
    _create_equipes_config(conn)
    _create_gestores_config(conn)
    _create_filtros_salvos(conn)
    _create_user_column_prefs(conn)
    _create_line_flags(conn)


def _create_equipes_config(conn: Any) -> None:
    conn.execute("""
        CREATE TABLE IF NOT EXISTS equipes_config (
            id SERIAL PRIMARY KEY,
            nome VARCHAR(150) NOT NULL,
            segmento VARCHAR(100) NOT NULL,
            gestor VARCHAR(255),
            setor VARCHAR(255),
            ativo BOOLEAN NOT NULL DEFAULT TRUE,
            criado_em TIMESTAMPTZ NOT NULL DEFAULT NOW()
        )
    """)


def _create_gestores_config(conn: Any) -> None:
    conn.execute("""
        CREATE TABLE IF NOT EXISTS gestores_config (
            id SERIAL PRIMARY KEY,
            nome VARCHAR(255) NOT NULL,
            equipe VARCHAR(150),
            segmento VARCHAR(100),
            email VARCHAR(255),
            ativo BOOLEAN NOT NULL DEFAULT TRUE
        )
    """)


def _create_filtros_salvos(conn: Any) -> None:
    conn.execute("""
        CREATE TABLE IF NOT EXISTS filtros_salvos (
            id SERIAL PRIMARY KEY,
            usuario_id INTEGER NOT NULL,
            nome VARCHAR(100) NOT NULL,
            filtro_json JSONB NOT NULL,
            criado_em TIMESTAMPTZ NOT NULL DEFAULT NOW()
        )
    """)


def _create_user_column_prefs(conn: Any) -> None:
    conn.execute("""
        CREATE TABLE IF NOT EXISTS user_column_prefs (
            usuario_id INTEGER PRIMARY KEY,
            colunas_visiveis JSONB NOT NULL DEFAULT '[]',
            atualizado_em TIMESTAMPTZ NOT NULL DEFAULT NOW()
        )
    """)


def _create_line_flags(conn: Any) -> None:
    conn.execute("""
        CREATE TABLE IF NOT EXISTS line_flags (
            id SERIAL PRIMARY KEY,
            linha_id BIGINT NOT NULL,
            usuario_id INTEGER NOT NULL,
            cor VARCHAR(20) NOT NULL DEFAULT 'yellow',
            nota TEXT,
            criado_em TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            UNIQUE(linha_id, usuario_id)
        )
    """)
```

- [ ] **Step 2: Chamar migrations em `init_db` no repository.py**

Em `src/db/repository.py`, localizar a função `init_db()` e adicionar ao final do bloco postgres:

```python
# Dentro do bloco postgres de init_db(), após as tabelas existentes:
from src.db.migrations import run_migrations
run_migrations(cur)
conn.commit()
```

- [ ] **Step 3: Verificar execução**

```bash
cd "C:\Users\TI02\Desktop\Planilhas Telefones"
python -c "from src.db.repository import init_db; init_db(); print('OK')"
```
Esperado: `OK` sem erros.

- [ ] **Step 4: Commit**

```bash
git add src/db/migrations.py src/db/repository.py
git commit -m "feat: add migrations for equipes_config, gestores_config, filtros_salvos, user_column_prefs, line_flags"
```

---

## Task 2: Colunas Redefinidas

**Files:**
- Modify: `src/core/config.py`
- Modify: `app.py` (substituir DEFAULT_COLUMNS e todas as referências às colunas removidas)

- [ ] **Step 1: Adicionar `NEW_COLUMNS_ORDER` em `src/core/config.py`**

```python
# src/core/config.py — adicionar após as constantes de path existentes

NEW_COLUMNS_ORDER = [
    "Codigo",
    "Nome",
    "Equipe",
    "Linha",
    "E-mail",
    "Gerenciamento",
    "IMEI A",
    "IMEI B",
    "CHIP",
    "Aparelho",
    "Modelo",
    "Setor",
    "Cargo",
    "Desconto",
    "Perfil",
    "Empresa",
    "Ativo",
    "Numero de Serie",
    "Operadora",
]

# Colunas removidas do display (ainda existem no banco, só não aparecem na grade)
HIDDEN_COLUMNS = [
    "Nome de Guerra",
    "Data da Troca",
    "Data Retorno",
    "Data Ocorrência",
    "Data Solicitação TBS",
    "Motivo",
    "Observação",
    "Marca",
    "Patrimonio",
]
```

- [ ] **Step 2: Substituir `DEFAULT_COLUMNS` em `app.py` (linhas 91–120)**

```python
# app.py — substituir o bloco DEFAULT_COLUMNS existente
from src.core.config import NEW_COLUMNS_ORDER, HIDDEN_COLUMNS
DEFAULT_COLUMNS = NEW_COLUMNS_ORDER
```

- [ ] **Step 3: Atualizar `build_full_table` em `app.py` (linha ~784)**

Localizar a função `build_full_table` e substituir as referências aos blocos `cols_front` que usam colunas antigas:

```python
def build_full_table(df: pd.DataFrame) -> pd.DataFrame:
    from src.core.config import NEW_COLUMNS_ORDER
    existing_front = [c for c in NEW_COLUMNS_ORDER if c in df.columns]
    tail = [c for c in df.columns if c not in existing_front and not c.startswith("__")]
    return df[existing_front + tail]
```

- [ ] **Step 4: Atualizar as listas de colunas nos blocos `cols_front` do segmento (linhas ~978–990 e ~2086 e ~2442–2464)**

Substituir todos os blocos `cols_front = [...]` espalhados no código por:

```python
from src.core.config import NEW_COLUMNS_ORDER
cols_front = NEW_COLUMNS_ORDER
```

- [ ] **Step 5: Verificar app inicia sem erro**

```bash
streamlit run app.py
```
Esperado: app abre, tabela mostra apenas as 19 colunas na ordem definida.

- [ ] **Step 6: Commit**

```bash
git add src/core/config.py app.py
git commit -m "feat: redefine column order, remove unused columns from display"
```

---

## Task 3: Sidebar Prosper (substituir navbar top)

**Files:**
- Create: `src/components/sidebar.py`
- Modify: `app.py` (remover navbar top, chamar sidebar)

- [ ] **Step 1: Criar `src/components/sidebar.py`**

```python
# src/components/sidebar.py
"""Sidebar de navegação com visual Prosper."""
from __future__ import annotations
import base64
from pathlib import Path
import streamlit as st

SIDEBAR_BG = "#111827"
GOLD = "#f2c230"
TEXT_MUTED = "rgba(255,255,255,0.5)"
TEXT_ACTIVE = "#ffffff"

SEGMENTOS = ["Alimento", "Medicamento", "Promotores", "Internos", "Manutenção", "Roubo e Perda"]
MODOS = ["Linhas ativas", "Linhas desativadas"]

CSS_SIDEBAR = f"""
<style>
/* Sidebar container */
section[data-testid="stSidebar"] > div:first-child {{
    background-color: {SIDEBAR_BG} !important;
    padding: 0 !important;
}}
section[data-testid="stSidebar"] {{
    min-width: 220px !important;
    max-width: 220px !important;
}}
/* Esconder header e toolbar do Streamlit */
#MainMenu, header[data-testid="stHeader"], footer, div[data-testid="stToolbar"] {{
    display: none !important;
}}
/* Área principal sem padding top */
.block-container {{
    padding-top: 1rem !important;
    padding-bottom: 1rem !important;
}}
/* Sidebar: textos brancos */
section[data-testid="stSidebar"] label,
section[data-testid="stSidebar"] p,
section[data-testid="stSidebar"] span,
section[data-testid="stSidebar"] div {{
    color: {TEXT_ACTIVE} !important;
}}
/* Radio buttons da sidebar */
section[data-testid="stSidebar"] [data-testid="stRadio"] label {{
    color: {TEXT_MUTED} !important;
    font-size: 0.875rem;
}}
section[data-testid="stSidebar"] [data-testid="stRadio"] label[data-selected="true"],
section[data-testid="stSidebar"] [data-testid="stRadio"] input:checked + div {{
    color: {TEXT_ACTIVE} !important;
    font-weight: 600;
}}
/* Dividers */
section[data-testid="stSidebar"] hr {{
    border-color: rgba(255,255,255,0.08) !important;
    margin: 8px 16px;
}}
/* Botões sidebar */
section[data-testid="stSidebar"] button {{
    background: transparent !important;
    border: 1px solid rgba(255,255,255,0.15) !important;
    color: {TEXT_MUTED} !important;
    border-radius: 6px;
    font-size: 0.8rem;
    width: 100%;
}}
section[data-testid="stSidebar"] button:hover {{
    border-color: {GOLD} !important;
    color: {TEXT_ACTIVE} !important;
}}
/* Team headers na área principal */
.team-header {{
    background: linear-gradient(90deg, #1a2e1a 0%, #2d4a2d 100%);
    border-left: 4px solid {GOLD};
    color: {TEXT_ACTIVE} !important;
    padding: 10px 16px;
    border-radius: 0 8px 8px 0;
    margin: 20px 0 4px 0;
    font-weight: 600;
    font-size: 1rem;
}}
.team-header-inactive {{
    background: linear-gradient(90deg, #2e1a1a 0%, #4a2d2d 100%);
    border-left: 4px solid #ef4444;
    color: {TEXT_ACTIVE} !important;
    padding: 10px 16px;
    border-radius: 0 8px 8px 0;
    margin: 20px 0 4px 0;
    font-weight: 600;
    font-size: 1rem;
}}
/* Tabela de equipes */
.tbl-equipe {{
    width: 100%;
    border-collapse: collapse;
    margin-bottom: 24px;
    font-size: 0.875rem;
    border-radius: 8px;
    overflow: hidden;
    box-shadow: 0 1px 3px rgba(0,0,0,0.1);
}}
.tbl-equipe thead tr {{ background: {SIDEBAR_BG}; }}
.tbl-equipe thead th {{ color: {GOLD} !important; font-weight: 600; padding: 10px 12px; text-align: left; }}
.tbl-equipe tbody tr:nth-child(even) {{ background: #f9fafb; }}
.tbl-equipe tbody tr:hover {{ background: #f0f4f0; }}
.tbl-equipe th, .tbl-equipe td {{ padding: 9px 12px; border-bottom: 1px solid #e5e7eb; white-space: nowrap; }}
.tbl-equipe tr.row-supervisor {{ background: #f0fdf4 !important; }}
.tbl-equipe tr.row-target {{ background: #fefce8 !important; box-shadow: inset 4px 0 0 {GOLD}; }}
.tbl-wrapper {{ overflow-x: auto; margin-bottom: 20px; }}
/* Flag colors em linhas */
.flag-red {{ background: #fef2f2 !important; border-left: 3px solid #ef4444 !important; }}
.flag-yellow {{ background: #fefce8 !important; border-left: 3px solid {GOLD} !important; }}
.flag-green {{ background: #f0fdf4 !important; border-left: 3px solid #22c55e !important; }}
</style>
"""


def render_sidebar(user: dict, current_page: str) -> dict:
    """
    Renderiza sidebar Prosper. Retorna dict com seleções do usuário:
    {modo, segmento, pagina, logout_clicked}
    """
    st.markdown(CSS_SIDEBAR, unsafe_allow_html=True)

    with st.sidebar:
        # Logo + título
        logo_path = Path("assets/logo.png")
        if logo_path.exists():
            logo_b64 = base64.b64encode(logo_path.read_bytes()).decode()
            st.markdown(
                f"""
                <div style="padding:20px 16px 12px;display:flex;align-items:center;gap:10px;">
                    <img src="data:image/png;base64,{logo_b64}" style="width:36px;height:auto;" />
                    <div>
                        <div style="color:#fff;font-weight:700;font-size:0.85rem;line-height:1.2;">Gerenciamento</div>
                        <div style="color:{GOLD};font-size:0.75rem;">de Telefones</div>
                    </div>
                </div>
                """,
                unsafe_allow_html=True,
            )
        else:
            st.markdown(
                f'<div style="padding:20px 16px 12px;color:#fff;font-weight:700;">Gerenciamento</div>',
                unsafe_allow_html=True,
            )

        st.divider()

        # Modo
        st.markdown(
            '<p style="color:rgba(255,255,255,0.4);font-size:0.7rem;text-transform:uppercase;'
            'letter-spacing:.08em;margin:4px 0 4px 0;padding-left:4px;">Modo</p>',
            unsafe_allow_html=True,
        )
        modo = st.radio(
            "modo",
            MODOS,
            index=MODOS.index(st.session_state.get("nav_modo", "Linhas ativas")),
            key="sidebar_modo",
            label_visibility="collapsed",
        )

        st.divider()

        # Segmento
        st.markdown(
            '<p style="color:rgba(255,255,255,0.4);font-size:0.7rem;text-transform:uppercase;'
            'letter-spacing:.08em;margin:4px 0 4px 0;padding-left:4px;">Segmento</p>',
            unsafe_allow_html=True,
        )
        segmento = st.radio(
            "segmento",
            SEGMENTOS,
            index=SEGMENTOS.index(st.session_state.get("nav_segmento", "Alimento")),
            key="sidebar_segmento",
            label_visibility="collapsed",
        )

        st.divider()

        # Navegação de páginas
        pagina = current_page
        if st.button("Painel de linhas", use_container_width=True):
            pagina = "painel"
        if user.get("role") == "admin":
            if st.button("Config & Admin", use_container_width=True):
                pagina = "config"

        st.divider()

        # Rodapé: usuário + logout
        username = user.get("username") or user.get("email") or "Usuário"
        role_label = "Admin" if user.get("role") == "admin" else "Técnico"
        st.markdown(
            f"""
            <div style="padding:8px 4px 4px;">
                <div style="color:#fff;font-size:0.8rem;font-weight:600;">{username}</div>
                <div style="color:{TEXT_MUTED};font-size:0.7rem;">{role_label}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )
        logout_clicked = st.button("Sair", use_container_width=True, key="sidebar_logout")

    return {
        "modo": modo,
        "segmento": segmento,
        "pagina": pagina,
        "logout_clicked": logout_clicked,
    }
```

- [ ] **Step 2: Integrar sidebar em `app.py`**

Localizar a função `_render_main_content` (ou o bloco principal de renderização após login) e:

1. Remover o bloco CSS inline com a navbar top (linhas 1289–1406)
2. Remover o bloco `col_brand, col_modo, col_seg, col_cfg, col_chamados, col_logout = st.columns(...)` (linhas 1409 em diante)
3. Substituir pelo import e chamada:

```python
from src.components.sidebar import render_sidebar

nav = render_sidebar(
    user=st.session_state.get("user", {}),
    current_page=st.session_state.get("current_page", "painel"),
)

if nav["logout_clicked"]:
    encerrar_sessao(st.session_state.get("session_token", ""))
    for k in list(st.session_state.keys()):
        del st.session_state[k]
    st.rerun()

modo_db   = "ativas" if nav["modo"] == "Linhas ativas" else "desativadas"
segmento_sel = nav["segmento"]
current_page = nav["pagina"]
st.session_state["nav_modo"]     = nav["modo"]
st.session_state["nav_segmento"] = nav["segmento"]
st.session_state["current_page"] = current_page
```

- [ ] **Step 3: Verificar sidebar funciona**

```bash
streamlit run app.py
```
Esperado: sidebar escura com logo, modo e segmento funcionando, botões de navegação visíveis.

- [ ] **Step 4: Commit**

```bash
git add src/components/__init__.py src/components/sidebar.py app.py
git commit -m "feat: replace top navbar with Prosper dark sidebar"
```

---

## Task 4: Show/Hide Colunas por Usuário

**Files:**
- Create: `src/components/editor_linhas.py`
- Modify: `src/db/repository.py` (salvar/carregar prefs)
- Modify: `app.py` (usar editor_linhas em vez do data_editor inline)

- [ ] **Step 1: Adicionar funções de preferências em `src/db/repository.py`**

```python
def salvar_colunas_visiveis(usuario_id: int, colunas: list[str]) -> None:
    """Salva preferência de colunas visíveis do usuário."""
    import json
    with _get_postgres_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO user_column_prefs (usuario_id, colunas_visiveis, atualizado_em)
                VALUES (%s, %s, NOW())
                ON CONFLICT (usuario_id) DO UPDATE
                  SET colunas_visiveis = EXCLUDED.colunas_visiveis,
                      atualizado_em = NOW()
                """,
                (usuario_id, json.dumps(colunas)),
            )
        conn.commit()


def carregar_colunas_visiveis(usuario_id: int, default_cols: list[str]) -> list[str]:
    """Retorna colunas visíveis salvas ou o padrão."""
    import json
    try:
        with _get_postgres_conn() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT colunas_visiveis FROM user_column_prefs WHERE usuario_id = %s",
                    (usuario_id,),
                )
                row = cur.fetchone()
                if row and row[0]:
                    saved = json.loads(row[0]) if isinstance(row[0], str) else row[0]
                    # Filtrar colunas que ainda existem no padrão
                    return [c for c in saved if c in default_cols] or default_cols
    except Exception:
        pass
    return default_cols
```

- [ ] **Step 2: Criar seletor de colunas na sidebar**

Em `src/components/sidebar.py`, adicionar função `render_column_picker`:

```python
def render_column_picker(all_cols: list[str], visible_cols: list[str]) -> list[str]:
    """
    Renderiza multiselect na sidebar para ocultar/mostrar colunas.
    Retorna lista de colunas selecionadas.
    """
    with st.sidebar:
        st.divider()
        st.markdown(
            '<p style="color:rgba(255,255,255,0.4);font-size:0.7rem;text-transform:uppercase;'
            'letter-spacing:.08em;margin:4px 0 4px 0;padding-left:4px;">Colunas visíveis</p>',
            unsafe_allow_html=True,
        )
        selected = st.multiselect(
            "cols",
            options=all_cols,
            default=visible_cols,
            key="sidebar_col_picker",
            label_visibility="collapsed",
        )
        if not selected:
            return visible_cols  # nunca deixar sem nenhuma coluna
        return selected
```

- [ ] **Step 3: Integrar em `app.py` no fluxo do painel**

```python
from src.db.repository import salvar_colunas_visiveis, carregar_colunas_visiveis
from src.components.sidebar import render_column_picker
from src.core.config import NEW_COLUMNS_ORDER

uid = st.session_state.get("user", {}).get("id")
if uid:
    visible_cols = carregar_colunas_visiveis(uid, NEW_COLUMNS_ORDER)
else:
    visible_cols = NEW_COLUMNS_ORDER

new_visible = render_column_picker(NEW_COLUMNS_ORDER, visible_cols)
if new_visible != visible_cols and uid:
    salvar_colunas_visiveis(uid, new_visible)
    visible_cols = new_visible
```

- [ ] **Step 4: Passar `visible_cols` para o data_editor**

No bloco que monta o `st.data_editor`, filtrar colunas:

```python
# Antes do st.data_editor, filtrar df para mostrar apenas visible_cols + colunas de controle
control_cols = ["↕ Ordem", "Mover equipe", "Selecionar", "__row_key"]
display_cols = [c for c in visible_cols if c in segment_atual.columns] + \
               [c for c in control_cols if c in segment_atual.columns]
df_to_edit = segment_atual[display_cols]
```

- [ ] **Step 5: Commit**

```bash
git add src/components/sidebar.py src/db/repository.py app.py
git commit -m "feat: show/hide columns per user with persistent preferences"
```

---

## Task 5: Filtros Salvos

**Files:**
- Create: `src/components/filtros.py`
- Modify: `src/db/repository.py`
- Modify: `app.py`

- [ ] **Step 1: Funções de filtros no `repository.py`**

```python
def salvar_filtro(usuario_id: int, nome: str, filtro: dict) -> None:
    """Salva filtro nomeado para o usuário."""
    import json
    with _get_postgres_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO filtros_salvos (usuario_id, nome, filtro_json)
                VALUES (%s, %s, %s)
                ON CONFLICT DO NOTHING
                """,
                (usuario_id, nome, json.dumps(filtro, ensure_ascii=False)),
            )
        conn.commit()


def listar_filtros(usuario_id: int) -> list[dict]:
    """Retorna filtros salvos do usuário."""
    import json
    try:
        with _get_postgres_conn() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT id, nome, filtro_json FROM filtros_salvos WHERE usuario_id = %s ORDER BY criado_em",
                    (usuario_id,),
                )
                rows = cur.fetchall()
                return [
                    {"id": r[0], "nome": r[1],
                     "filtro": json.loads(r[2]) if isinstance(r[2], str) else r[2]}
                    for r in rows
                ]
    except Exception:
        return []


def excluir_filtro(filtro_id: int, usuario_id: int) -> None:
    """Remove filtro do usuário."""
    with _get_postgres_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "DELETE FROM filtros_salvos WHERE id = %s AND usuario_id = %s",
                (filtro_id, usuario_id),
            )
        conn.commit()
```

- [ ] **Step 2: Criar `src/components/filtros.py`**

```python
# src/components/filtros.py
"""Componente de filtros salvos."""
from __future__ import annotations
import streamlit as st


def render_filtros_salvos(
    usuario_id: int,
    filtros: list[dict],
    on_aplicar,
    on_excluir,
) -> None:
    """
    Renderiza seção de filtros salvos na sidebar.
    on_aplicar(filtro: dict) -> None
    on_excluir(filtro_id: int) -> None
    """
    import streamlit as st
    with st.sidebar:
        st.markdown(
            '<p style="color:rgba(255,255,255,0.4);font-size:0.7rem;text-transform:uppercase;'
            'letter-spacing:.08em;margin:4px 0 4px 0;padding-left:4px;">Filtros salvos</p>',
            unsafe_allow_html=True,
        )
        if not filtros:
            st.caption("Nenhum filtro salvo.")
        else:
            for f in filtros:
                col_a, col_b = st.columns([3, 1])
                with col_a:
                    if st.button(f["nome"], key=f"filtro_apply_{f['id']}", use_container_width=True):
                        on_aplicar(f["filtro"])
                with col_b:
                    if st.button("✕", key=f"filtro_del_{f['id']}"):
                        on_excluir(f["id"])
                        st.rerun()


def render_salvar_filtro_atual(filtro_atual: dict, on_salvar) -> None:
    """Formulário inline para salvar filtro atual com nome."""
    with st.expander("Salvar filtro atual", expanded=False):
        nome = st.text_input("Nome do filtro", key="novo_filtro_nome", placeholder="Ex.: Vendedores Baixada")
        if st.button("Salvar", key="btn_salvar_filtro") and nome.strip():
            on_salvar(nome.strip(), filtro_atual)
            st.success(f"Filtro '{nome}' salvo!")
            st.rerun()
```

- [ ] **Step 3: Integrar em `app.py`**

```python
from src.components.filtros import render_filtros_salvos, render_salvar_filtro_atual
from src.db.repository import salvar_filtro, listar_filtros, excluir_filtro

uid = st.session_state.get("user", {}).get("id")
filtros_do_usuario = listar_filtros(uid) if uid else []

filtro_atual = {
    "segmento": segmento_sel,
    "modo": modo_db,
    "busca": st.session_state.get("filtro_busca", ""),
    "somente_vagas": st.session_state.get("filtro_somente_vagas", False),
}

def aplicar_filtro(f: dict):
    if "segmento" in f:
        st.session_state["nav_segmento"] = f["segmento"]
    if "busca" in f:
        st.session_state["filtro_busca"] = f["busca"]
    if "somente_vagas" in f:
        st.session_state["filtro_somente_vagas"] = f["somente_vagas"]

render_filtros_salvos(
    usuario_id=uid,
    filtros=filtros_do_usuario,
    on_aplicar=aplicar_filtro,
    on_excluir=lambda fid: excluir_filtro(fid, uid),
)

render_salvar_filtro_atual(
    filtro_atual=filtro_atual,
    on_salvar=lambda nome, f: salvar_filtro(uid, nome, f),
)
```

- [ ] **Step 4: Commit**

```bash
git add src/components/filtros.py src/db/repository.py app.py
git commit -m "feat: saved filters with apply and delete per user"
```

---

## Task 6: Agrupamento Alternativo

**Files:**
- Modify: `app.py` (adicionar toggle de agrupamento antes do data editor)

- [ ] **Step 1: Adicionar seletor de agrupamento na sidebar**

Em `src/components/sidebar.py`, adicionar ao final de `render_sidebar`:

```python
# Dentro de render_sidebar(), antes do divider do rodapé:
st.divider()
st.markdown(
    '<p style="color:rgba(255,255,255,0.4);font-size:0.7rem;text-transform:uppercase;'
    'letter-spacing:.08em;margin:4px 0 4px 0;padding-left:4px;">Agrupar por</p>',
    unsafe_allow_html=True,
)
agrupar_por = st.radio(
    "agrupar_por",
    ["Equipe", "Setor", "Gestor", "Cargo"],
    index=0,
    key="sidebar_agrupar_por",
    label_visibility="collapsed",
)
# Adicionar ao dict de retorno:
# "agrupar_por": agrupar_por
```

Atualizar o `return` do `render_sidebar` para incluir `"agrupar_por": agrupar_por`.

- [ ] **Step 2: Implementar agrupamento no loop de renderização**

Em `app.py`, localizar o loop `for eq_nome, segment_atual in ...` que itera por equipe e adicionar suporte ao agrupamento alternativo:

```python
agrupar_por = nav.get("agrupar_por", "Equipe")

COL_MAP = {
    "Equipe": "EquipePadrao",
    "Setor": "Setor",
    "Gestor": "Gestor",
    "Cargo": "Cargo",
}
group_col = COL_MAP.get(agrupar_por, "EquipePadrao")

# Substituir o agrupamento existente por:
df_segmento = df_full[df_full["Segmento"].str.strip().str.lower() == segmento_sel.strip().lower()].copy()
grupos = df_segmento.groupby(
    df_segmento[group_col].fillna("Sem " + agrupar_por).str.strip(),
    sort=True,
)
for grupo_nome, segment_atual in grupos:
    # ... renderizar header e data_editor para cada grupo
    header_html = f'<div class="team-header">{grupo_nome}</div>'
    st.markdown(header_html, unsafe_allow_html=True)
```

- [ ] **Step 3: Verificar agrupamentos**

```bash
streamlit run app.py
```
Esperado: ao mudar "Agrupar por" na sidebar, a tabela se reorganiza por Setor/Gestor/Cargo sem perder funcionalidade de edição.

- [ ] **Step 4: Commit**

```bash
git add src/components/sidebar.py app.py
git commit -m "feat: alternative grouping by equipe/setor/gestor/cargo"
```

---

## Task 7: Destaque de Linhas (Flags)

**Files:**
- Modify: `src/db/repository.py`
- Modify: `app.py` (adicionar coluna de flag no data editor + ações de flag)

- [ ] **Step 1: Funções de flags no `repository.py`**

```python
def salvar_flag_linha(linha_id: int, usuario_id: int, cor: str, nota: str = "") -> None:
    """Adiciona ou atualiza flag em uma linha."""
    with _get_postgres_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO line_flags (linha_id, usuario_id, cor, nota)
                VALUES (%s, %s, %s, %s)
                ON CONFLICT (linha_id, usuario_id) DO UPDATE
                  SET cor = EXCLUDED.cor, nota = EXCLUDED.nota
                """,
                (linha_id, usuario_id, cor, nota),
            )
        conn.commit()


def remover_flag_linha(linha_id: int, usuario_id: int) -> None:
    """Remove flag de uma linha."""
    with _get_postgres_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "DELETE FROM line_flags WHERE linha_id = %s AND usuario_id = %s",
                (linha_id, usuario_id),
            )
        conn.commit()


def listar_flags_usuario(usuario_id: int) -> dict[int, str]:
    """Retorna dict {linha_id: cor} para o usuário."""
    try:
        with _get_postgres_conn() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT linha_id, cor FROM line_flags WHERE usuario_id = %s",
                    (usuario_id,),
                )
                return {r[0]: r[1] for r in cur.fetchall()}
    except Exception:
        return {}
```

- [ ] **Step 2: Coluna de flag no data editor**

Em `app.py`, antes de exibir o `st.data_editor`, adicionar coluna `🏳 Flag`:

```python
from src.db.repository import listar_flags_usuario

uid = st.session_state.get("user", {}).get("id")
flags = listar_flags_usuario(uid) if uid else {}

# Adicionar coluna __flag ao df antes do editor
COR_EMOJI = {"red": "🔴", "yellow": "🟡", "green": "🟢", "": ""}
if "id" in segment_atual.columns:
    segment_atual["🏳 Flag"] = segment_atual["id"].map(
        lambda lid: COR_EMOJI.get(flags.get(lid, ""), "")
    )
```

- [ ] **Step 3: UI de flag nas ações de equipe**

Dentro de cada expander de ações, adicionar seção de flag:

```python
st.markdown("**Destacar linha**")
flag_linha_alvo = st.text_input("Número da linha para destacar", key=f"flag_linha_{key_base}")
flag_cor = st.selectbox("Cor", ["🟡 Amarelo", "🔴 Vermelho", "🟢 Verde"], key=f"flag_cor_{key_base}")
flag_nota = st.text_input("Nota (opcional)", key=f"flag_nota_{key_base}")
cor_map = {"🟡 Amarelo": "yellow", "🔴 Vermelho": "red", "🟢 Verde": "green"}
col_f1, col_f2 = st.columns(2)
with col_f1:
    if st.button("Destacar", key=f"btn_flag_{key_base}"):
        linha_match = segment_atual[segment_atual["Linha"].astype(str).str.strip() == flag_linha_alvo.strip()]
        if not linha_match.empty and uid:
            salvar_flag_linha(int(linha_match.iloc[0]["id"]), uid, cor_map[flag_cor], flag_nota)
            st.success("Linha destacada!")
            st.rerun()
with col_f2:
    if st.button("Remover destaque", key=f"btn_unflag_{key_base}"):
        linha_match = segment_atual[segment_atual["Linha"].astype(str).str.strip() == flag_linha_alvo.strip()]
        if not linha_match.empty and uid:
            remover_flag_linha(int(linha_match.iloc[0]["id"]), uid)
            st.rerun()
```

- [ ] **Step 4: Commit**

```bash
git add src/db/repository.py app.py
git commit -m "feat: line flags with red/yellow/green colors per user"
```

---

## Task 8: Adicionar Linha Rápida

**Files:**
- Modify: `app.py` (formulário inline no topo de cada equipe)

- [ ] **Step 1: Adicionar form de linha rápida antes do data editor**

Logo antes de renderizar o `st.data_editor` de cada grupo/equipe:

```python
with st.expander("➕ Adicionar linha rápida", expanded=False):
    rl_col1, rl_col2, rl_col3, rl_col4 = st.columns(4)
    with rl_col1:
        rl_numero = st.text_input("Número da linha *", key=f"rl_numero_{key_base}", placeholder="21999990000")
    with rl_col2:
        rl_nome = st.text_input("Nome (ou VAGO)", key=f"rl_nome_{key_base}", placeholder="VAGO")
    with rl_col3:
        rl_imei = st.text_input("IMEI A", key=f"rl_imei_{key_base}")
    with rl_col4:
        rl_aparelho = st.text_input("Aparelho", key=f"rl_aparelho_{key_base}")

    if st.button("Adicionar", key=f"btn_rl_{key_base}", type="primary"):
        if not rl_numero.strip():
            st.warning("Número da linha é obrigatório.")
        else:
            df_all = load_linhas(modo=modo_db)
            existing = df_all[df_all["Linha"].astype(str).str.strip() == rl_numero.strip()]
            if not existing.empty:
                st.error(f"Linha {rl_numero} já existe.")
            else:
                nova = pd.DataFrame([{
                    "Linha": rl_numero.strip(),
                    "Nome": rl_nome.strip() or "VAGO",
                    "IMEI A": rl_imei.strip(),
                    "Aparelho": rl_aparelho.strip(),
                    "EquipePadrao": eq_nome,
                    "Equipe": eq_nome,
                    "Segmento": segmento_sel,
                    "GrupoEquipe": segmento_sel,
                }])
                df_all = pd.concat([nova, df_all], ignore_index=True)
                save_linhas(df_all, modo=modo_db)
                _audit(
                    acao="criar_linha",
                    entidade="linhas",
                    chave=rl_numero.strip(),
                    antes={},
                    depois=nova.iloc[0].to_dict(),
                    detalhes=f"Linha rápida adicionada à equipe {eq_nome}.",
                )
                st.success(f"Linha {rl_numero} adicionada!")
                st.rerun()
```

- [ ] **Step 2: Commit**

```bash
git add app.py
git commit -m "feat: quick add line form at top of each team section"
```

---

## Task 9: Aba Admin — Gestão de Equipes e Gestores

**Files:**
- Create: `src/pages/config_admin.py`
- Modify: `src/db/repository.py`
- Modify: `app.py` (rotear para config_admin quando pagina == "config")

- [ ] **Step 1: Funções CRUD de equipes no `repository.py`**

```python
def listar_equipes_config() -> list[dict]:
    """Lista equipes cadastradas."""
    try:
        with _get_postgres_conn() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT id, nome, segmento, gestor, setor, ativo FROM equipes_config ORDER BY segmento, nome"
                )
                cols = ["id", "nome", "segmento", "gestor", "setor", "ativo"]
                return [dict(zip(cols, r)) for r in cur.fetchall()]
    except Exception:
        return []


def salvar_equipe_config(nome: str, segmento: str, gestor: str, setor: str, equipe_id: int | None = None) -> None:
    with _get_postgres_conn() as conn:
        with conn.cursor() as cur:
            if equipe_id:
                cur.execute(
                    "UPDATE equipes_config SET nome=%s, segmento=%s, gestor=%s, setor=%s WHERE id=%s",
                    (nome, segmento, gestor, setor, equipe_id),
                )
            else:
                cur.execute(
                    "INSERT INTO equipes_config (nome, segmento, gestor, setor) VALUES (%s,%s,%s,%s)",
                    (nome, segmento, gestor, setor),
                )
        conn.commit()


def excluir_equipe_config(equipe_id: int) -> None:
    with _get_postgres_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("DELETE FROM equipes_config WHERE id=%s", (equipe_id,))
        conn.commit()


def listar_gestores_config() -> list[dict]:
    try:
        with _get_postgres_conn() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT id, nome, equipe, segmento, email, ativo FROM gestores_config ORDER BY nome")
                cols = ["id", "nome", "equipe", "segmento", "email", "ativo"]
                return [dict(zip(cols, r)) for r in cur.fetchall()]
    except Exception:
        return []


def salvar_gestor_config(nome: str, equipe: str, segmento: str, email: str, gestor_id: int | None = None) -> None:
    with _get_postgres_conn() as conn:
        with conn.cursor() as cur:
            if gestor_id:
                cur.execute(
                    "UPDATE gestores_config SET nome=%s, equipe=%s, segmento=%s, email=%s WHERE id=%s",
                    (nome, equipe, segmento, email, gestor_id),
                )
            else:
                cur.execute(
                    "INSERT INTO gestores_config (nome, equipe, segmento, email) VALUES (%s,%s,%s,%s)",
                    (nome, equipe, segmento, email),
                )
        conn.commit()


def excluir_gestor_config(gestor_id: int) -> None:
    with _get_postgres_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("DELETE FROM gestores_config WHERE id=%s", (gestor_id,))
        conn.commit()
```

- [ ] **Step 2: Criar `src/pages/config_admin.py`**

```python
# src/pages/config_admin.py
"""Página de administração: equipes, gestores, usuários."""
from __future__ import annotations
import streamlit as st
import pandas as pd
from src.db.repository import (
    listar_equipes_config, salvar_equipe_config, excluir_equipe_config,
    listar_gestores_config, salvar_gestor_config, excluir_gestor_config,
    listar_usuarios, criar_usuario, excluir_usuario, atualizar_senha_usuario,
    listar_auditoria,
)

SEGMENTOS = ["Alimento", "Medicamento", "Promotores", "Internos", "Manutenção", "Roubo e Perda"]


def render_config_admin() -> None:
    st.title("Configurações & Administração")
    tab_equipes, tab_gestores, tab_usuarios, tab_auditoria = st.tabs([
        "Equipes", "Gestores / Gerência", "Usuários", "Auditoria"
    ])

    with tab_equipes:
        _render_equipes()

    with tab_gestores:
        _render_gestores()

    with tab_usuarios:
        _render_usuarios()

    with tab_auditoria:
        _render_auditoria()


def _render_equipes() -> None:
    st.subheader("Equipes cadastradas")
    equipes = listar_equipes_config()
    if equipes:
        df = pd.DataFrame(equipes)
        st.dataframe(df[["nome", "segmento", "gestor", "setor", "ativo"]], hide_index=True, use_container_width=True)

    st.divider()
    st.subheader("Adicionar / Editar equipe")
    ids = ["Nova equipe"] + [f"{e['id']} — {e['nome']}" for e in equipes]
    sel = st.selectbox("Selecione para editar ou 'Nova equipe'", ids, key="eq_sel")
    edit_id = None
    defaults = {"nome": "", "segmento": SEGMENTOS[0], "gestor": "", "setor": ""}
    if sel != "Nova equipe":
        edit_id = int(sel.split(" — ")[0])
        found = next((e for e in equipes if e["id"] == edit_id), None)
        if found:
            defaults = found

    col1, col2 = st.columns(2)
    with col1:
        nome_eq = st.text_input("Nome da equipe", value=defaults["nome"], key="eq_nome")
        seg_eq = st.selectbox("Segmento", SEGMENTOS,
                              index=SEGMENTOS.index(defaults["segmento"]) if defaults["segmento"] in SEGMENTOS else 0,
                              key="eq_seg")
    with col2:
        gestor_eq = st.text_input("Gestor", value=defaults.get("gestor") or "", key="eq_gestor")
        setor_eq = st.text_input("Setor", value=defaults.get("setor") or "", key="eq_setor")

    c_save, c_del = st.columns(2)
    with c_save:
        if st.button("Salvar equipe", key="btn_save_eq", type="primary"):
            if nome_eq.strip():
                salvar_equipe_config(nome_eq.strip(), seg_eq, gestor_eq.strip(), setor_eq.strip(), edit_id)
                st.success("Equipe salva!")
                st.rerun()
    with c_del:
        if edit_id and st.button("Excluir equipe", key="btn_del_eq"):
            excluir_equipe_config(edit_id)
            st.warning("Equipe excluída.")
            st.rerun()


def _render_gestores() -> None:
    st.subheader("Gestores / Gerência")
    gestores = listar_gestores_config()
    if gestores:
        df = pd.DataFrame(gestores)
        st.dataframe(df[["nome", "equipe", "segmento", "email", "ativo"]], hide_index=True, use_container_width=True)

    st.divider()
    st.subheader("Adicionar / Editar gestor")
    ids = ["Novo gestor"] + [f"{g['id']} — {g['nome']}" for g in gestores]
    sel = st.selectbox("Selecione para editar ou 'Novo gestor'", ids, key="gest_sel")
    edit_id = None
    defaults = {"nome": "", "equipe": "", "segmento": "", "email": ""}
    if sel != "Novo gestor":
        edit_id = int(sel.split(" — ")[0])
        found = next((g for g in gestores if g["id"] == edit_id), None)
        if found:
            defaults = found

    col1, col2 = st.columns(2)
    with col1:
        nome_g = st.text_input("Nome completo", value=defaults["nome"], key="g_nome")
        equipe_g = st.text_input("Equipe", value=defaults.get("equipe") or "", key="g_equipe")
    with col2:
        seg_g = st.selectbox("Segmento", [""] + SEGMENTOS,
                             index=([""] + SEGMENTOS).index(defaults.get("segmento") or "")
                             if (defaults.get("segmento") or "") in ([""] + SEGMENTOS) else 0,
                             key="g_seg")
        email_g = st.text_input("E-mail", value=defaults.get("email") or "", key="g_email")

    c_save, c_del = st.columns(2)
    with c_save:
        if st.button("Salvar gestor", key="btn_save_g", type="primary"):
            if nome_g.strip():
                salvar_gestor_config(nome_g.strip(), equipe_g.strip(), seg_g, email_g.strip(), edit_id)
                st.success("Gestor salvo!")
                st.rerun()
    with c_del:
        if edit_id and st.button("Excluir gestor", key="btn_del_g"):
            excluir_gestor_config(edit_id)
            st.warning("Gestor excluído.")
            st.rerun()


def _render_usuarios() -> None:
    st.subheader("Usuários do sistema")
    usuarios = listar_usuarios() or []
    if usuarios:
        df_u = pd.DataFrame(usuarios)[["username", "role", "ativo"]] if usuarios else pd.DataFrame()
        st.dataframe(df_u, hide_index=True, use_container_width=True)

    st.divider()
    st.subheader("Criar usuário")
    col1, col2, col3 = st.columns(3)
    with col1:
        new_user = st.text_input("Username", key="new_user")
    with col2:
        new_pass = st.text_input("Senha", type="password", key="new_pass")
    with col3:
        new_role = st.selectbox("Papel", ["tecnico", "admin"], key="new_role")
    if st.button("Criar", key="btn_criar_user", type="primary"):
        if new_user.strip() and new_pass.strip():
            ok, msg = criar_usuario(new_user.strip(), new_pass.strip(), new_role)
            if ok:
                st.success(f"Usuário {new_user} criado.")
                st.rerun()
            else:
                st.error(msg)


def _render_auditoria() -> None:
    st.subheader("Log de auditoria")
    ticket_filter = st.text_input("Filtrar por ticket ID (opcional)", key="audit_ticket")
    logs = listar_auditoria(chamado_id=ticket_filter.strip() or None, limit=500) or []
    if logs:
        df_log = pd.DataFrame(logs)
        st.dataframe(df_log, hide_index=True, use_container_width=True)
    else:
        st.info("Nenhum registro encontrado.")
```

- [ ] **Step 3: Rotear config_admin em `app.py`**

```python
from src.pages.config_admin import render_config_admin

if current_page == "config" and st.session_state.get("user", {}).get("role") == "admin":
    render_config_admin()
else:
    # ... render painel normal
    pass
```

- [ ] **Step 4: Commit**

```bash
git add src/pages/__init__.py src/pages/config_admin.py src/db/repository.py app.py
git commit -m "feat: admin config tab with equipes, gestores, usuarios, auditoria"
```

---

## Task 10: Polimento Final — Testes e Ajustes

**Files:**
- Modify: `app.py` (ajustes visuais finais)

- [ ] **Step 1: Verificar fluxo completo**

```bash
streamlit run app.py
```
Checklist:
- [ ] Sidebar carrega com logo e cores Prosper
- [ ] Modo (Ativas/Desativadas) funciona via sidebar
- [ ] Segmento funciona via sidebar
- [ ] Tabela exibe apenas as 19 colunas na ordem correta
- [ ] Show/hide colunas salva entre sessões
- [ ] Filtros salvos: salvar, aplicar e excluir
- [ ] Agrupamento por Equipe/Setor/Gestor/Cargo funciona
- [ ] Flag em linha aparece na coluna 🏳
- [ ] Linha rápida adiciona ao banco
- [ ] Aba Admin abre para usuário admin
- [ ] CRUD de equipes e gestores funciona
- [ ] Auditoria exibe logs

- [ ] **Step 2: Ajustes de margem/padding**

```python
# No CSS_SIDEBAR em sidebar.py, ajustar padding da área principal:
.block-container {
    padding-top: 1rem !important;
    padding-left: 1.5rem !important;
    padding-right: 1.5rem !important;
    max-width: 100% !important;
}
```

- [ ] **Step 3: Commit final**

```bash
git add -A
git commit -m "feat: final polish — Gerenciamento de Telefones redesign complete"
```

---

## Resumo das Entregas

| # | Feature | Impacto |
|---|---------|---------|
| 1 | Migrations novas tabelas | Base para todas as features |
| 2 | Colunas redefinidas (19 colunas) | Menos poluição visual |
| 3 | Sidebar Prosper dark + gold | Visual igual ao Sistema de Chamados |
| 4 | Show/hide colunas por usuário | Autonomia individual |
| 5 | Filtros salvos | Produtividade |
| 6 | Agrupar por Equipe/Setor/Gestor/Cargo | Flexibilidade de visão |
| 7 | Flags de linha (vermelho/amarelo/verde) | Acompanhamento de pendências |
| 8 | Linha rápida inline | Agilidade |
| 9 | Aba Admin (equipes, gestores, usuários) | Autonomia do admin |
| 10 | Polimento final | Qualidade |
