"""Sidebar de navegação com visual Prosper — espelha o design do Sistema de Chamados TI."""
from __future__ import annotations
import base64
from pathlib import Path
import streamlit as st

# ── Paleta Prosper ──────────────────────────────────────────────────────────
SIDEBAR_BG  = "#111827"
GOLD        = "#f2c230"
TEXT_MUTED  = "rgba(255,255,255,0.85)"
TEXT_ACTIVE = "#ffffff"

SEGMENTOS = ["Alimento", "Medicamento", "Promotores", "Internos", "Manutenção", "Roubo e Perda"]
MODOS     = ["Linhas ativas", "Linhas desativadas"]

# ── CSS escuro (padrão Prosper) ──────────────────────────────────────────────
_CSS_DARK = f"""
<style>
/* ══════════════════════════════════════════════
   SIDEBAR
══════════════════════════════════════════════ */
section[data-testid="stSidebar"] > div:first-child {{
    background-color: {SIDEBAR_BG} !important;
    padding: 0 !important;
    margin-top: 0 !important;
}}
/* Esconder o container inteiro do botão colapsar (stSidebarHeader) */
[data-testid="stSidebarHeader"] {{
    display: none !important;
    height: 0 !important;
    min-height: 0 !important;
    padding: 0 !important;
    margin: 0 !important;
    overflow: hidden !important;
}}
/* Puxar o conteúdo para cima — compensa o espaço do header oculto no Streamlit 1.55 */
[data-testid="stSidebarContent"] {{
    margin-top: -3.5rem !important;
    padding-top: 0 !important;
}}
[data-testid="stSidebarUserContent"] {{
    padding-top: 0 !important;
    margin-top: 0 !important;
}}
section[data-testid="stSidebar"] .block-container {{
    padding-top: 0 !important;
    margin-top: 0 !important;
}}
section[data-testid="stSidebar"] {{
    min-width: 240px !important;
    max-width: 240px !important;
}}
/* Textos brancos dentro da sidebar */
section[data-testid="stSidebar"] label,
section[data-testid="stSidebar"] p,
section[data-testid="stSidebar"] span {{
    color: {TEXT_ACTIVE} !important;
}}
/* Radio */
section[data-testid="stSidebar"] [data-testid="stRadio"] label {{
    color: {TEXT_MUTED} !important;
    font-size: 0.875rem;
    padding: 2px 0;
}}
section[data-testid="stSidebar"] [data-testid="stRadio"] label:has(input:checked) {{
    color: {TEXT_ACTIVE} !important;
    font-weight: 600;
}}
/* Dividers */
section[data-testid="stSidebar"] hr {{
    border-color: rgba(255,255,255,0.08) !important;
    margin: 6px 16px;
}}
/* Botões sidebar — fundo escuro explícito (transparent quebra com base="light") */
section[data-testid="stSidebar"] button,
section[data-testid="stSidebar"] [data-testid^="stBaseButton"] {{
    background: #1a2332 !important;
    background-color: #1a2332 !important;
    border: 1px solid rgba(255,255,255,0.12) !important;
    color: {TEXT_MUTED} !important;
    border-radius: 6px !important;
    font-size: 0.82rem !important;
    width: 100% !important;
    transition: all .15s ease;
}}
section[data-testid="stSidebar"] button p,
section[data-testid="stSidebar"] button span,
section[data-testid="stSidebar"] [data-testid^="stBaseButton"] p,
section[data-testid="stSidebar"] [data-testid^="stBaseButton"] span {{
    color: {TEXT_MUTED} !important;
}}
section[data-testid="stSidebar"] button:hover,
section[data-testid="stSidebar"] [data-testid^="stBaseButton"]:hover {{
    border-color: {GOLD} !important;
    color: {TEXT_ACTIVE} !important;
    background: rgba(242,194,48,0.08) !important;
}}
section[data-testid="stSidebar"] button:hover p,
section[data-testid="stSidebar"] button:hover span,
section[data-testid="stSidebar"] [data-testid^="stBaseButton"]:hover p,
section[data-testid="stSidebar"] [data-testid^="stBaseButton"]:hover span {{
    color: {TEXT_ACTIVE} !important;
}}
/* Inputs dentro da sidebar */
section[data-testid="stSidebar"] input,
section[data-testid="stSidebar"] [data-baseweb="input"],
section[data-testid="stSidebar"] [data-baseweb="base-input"],
section[data-testid="stSidebar"] [data-baseweb="input"] input,
section[data-testid="stSidebar"] [data-baseweb="base-input"] input {{
    background: #1e293b !important;
    background-color: #1e293b !important;
    color: #e2e8f0 !important;
    border-color: #475569 !important;
    caret-color: #e2e8f0 !important;
}}
/* Multiselect sidebar */
section[data-testid="stSidebar"] [data-baseweb="select"] > div,
section[data-testid="stSidebar"] .stMultiSelect > div > div {{
    background: #1e293b !important;
    background-color: #1e293b !important;
    border-color: #475569 !important;
    color: #e2e8f0 !important;
}}
section[data-testid="stSidebar"] [data-baseweb="tag"] {{
    background: #334155 !important;
    background-color: #334155 !important;
    color: #e2e8f0 !important;
    border-radius: 4px !important;
}}
section[data-testid="stSidebar"] [data-baseweb="tag"] span,
section[data-testid="stSidebar"] [data-baseweb="tag"] button {{
    color: #e2e8f0 !important;
}}
/* Expander sidebar (ex: Salvar filtro atual) */
section[data-testid="stSidebar"] [data-testid="stExpander"] {{
    background: #1e293b !important;
    background-color: #1e293b !important;
    border: 1px solid #334155 !important;
    border-radius: 8px !important;
}}
section[data-testid="stSidebar"] [data-testid="stExpander"] summary,
section[data-testid="stSidebar"] [data-testid="stExpander"] summary p,
section[data-testid="stSidebar"] [data-testid="stExpander"] summary span {{
    color: #e2e8f0 !important;
    background: transparent !important;
}}
section[data-testid="stSidebar"] [data-testid="stExpander"] > div {{
    background: #1e293b !important;
    background-color: #1e293b !important;
}}
/* Ocultar chrome do Streamlit */
#MainMenu, header[data-testid="stHeader"], footer, div[data-testid="stToolbar"] {{
    display: none !important;
}}
/* Ocultar botão «/» de colapsar sidebar */
[data-testid="stBaseButton-headerNoPadding"],
button[data-testid="baseButton-headerNoPadding"],
[data-testid="stSidebarCollapseButton"],
[data-testid="collapsedControl"] {{
    display: none !important;
}}
/* Ocultar seta/chevron do st.popover */
[data-testid="stPopover"] > div > button svg {{
    display: none !important;
}}
/* Estilo do botão popover (Adicionar) */
[data-testid="stPopover"] > div > button {{
    background: #1e293b !important;
    color: #e2e8f0 !important;
    border: 1px solid #475569 !important;
    border-radius: 6px !important;
    font-weight: 600 !important;
    height: 2.5rem !important;
    padding: 0 1rem !important;
    white-space: nowrap !important;
    font-size: 0.875rem !important;
}}
[data-testid="stPopover"] > div > button:hover {{
    border-color: {GOLD} !important;
    color: {GOLD} !important;
    background: rgba(242,194,48,0.08) !important;
}}
.block-container,
[data-testid="stMainBlockContainer"],
[data-testid="stMain"] > div:first-child {{
    padding-top: 0 !important;
    padding-bottom: 1rem !important;
    max-width: 100% !important;
}}

/* ══════════════════════════════════════════════
   APP SHELL — Streamlit 1.55 selectors
══════════════════════════════════════════════ */
.stApp,
[data-testid="stAppViewContainer"],
[data-testid="stMain"],
[data-testid="stMainBlockContainer"] {{
    background-color: #0f172a !important;
    color: #e2e8f0 !important;
}}
.stApp .block-container,
[data-testid="stMain"] .block-container,
[data-testid="stMainBlockContainer"] {{
    background-color: #0f172a !important;
    max-width: 100% !important;
}}
body {{
    background-color: #0f172a !important;
}}

/* ══════════════════════════════════════════════
   TIPOGRAFIA
══════════════════════════════════════════════ */
.stApp h1, .stApp h2, .stApp h3, .stApp h4, .stApp h5, .stApp h6,
[data-testid="stMain"] h1, [data-testid="stMain"] h2,
[data-testid="stMain"] h3, [data-testid="stMain"] h4 {{
    color: #f1f5f9 !important;
}}
.stApp p, .stApp li,
[data-testid="stMain"] p, [data-testid="stMain"] li {{
    color: #cbd5e1 !important;
}}
.stApp label,
[data-testid="stMain"] label {{
    color: #cbd5e1 !important;
}}
.stApp .stCaption p, .stApp .stCaption,
[data-testid="stMain"] .stCaption p {{
    color: #94a3b8 !important;
}}
.stMarkdown p, .stMarkdown li {{
    color: #cbd5e1 !important;
}}
.stApp hr,
[data-testid="stMain"] hr {{
    border-color: #334155 !important;
}}

/* ══════════════════════════════════════════════
   FORMULÁRIOS
══════════════════════════════════════════════ */
[data-testid="stForm"] {{
    background: #1e293b !important;
    border: 1px solid #334155 !important;
    border-radius: 10px !important;
    padding: 20px !important;
}}

/* ══════════════════════════════════════════════
   INPUTS — BaseUI
══════════════════════════════════════════════ */
[data-baseweb="input"],
[data-baseweb="base-input"] {{
    background-color: #1e293b !important;
    border-color: #475569 !important;
}}
[data-baseweb="input"] input,
[data-baseweb="base-input"] input {{
    background-color: #1e293b !important;
    color: #e2e8f0 !important;
    caret-color: #e2e8f0 !important;
}}
[data-baseweb="input"]:focus-within,
[data-baseweb="base-input"]:focus-within {{
    border-color: {GOLD} !important;
}}
/* Streamlit text/number input wrapper */
.stTextInput input,
.stTextArea textarea,
.stNumberInput input {{
    background: #1e293b !important;
    color: #e2e8f0 !important;
    border: 1px solid #475569 !important;
    border-radius: 6px !important;
}}
.stTextInput input:focus,
.stTextArea textarea:focus,
.stNumberInput input:focus {{
    border-color: {GOLD} !important;
    box-shadow: 0 0 0 1px {GOLD}40 !important;
}}

/* ══════════════════════════════════════════════
   TEXTAREA — BaseUI
══════════════════════════════════════════════ */
[data-baseweb="textarea"] {{
    background-color: #1e293b !important;
    border-color: #475569 !important;
}}
[data-baseweb="textarea"] textarea {{
    background-color: #1e293b !important;
    color: #e2e8f0 !important;
}}

/* ══════════════════════════════════════════════
   SELECT / MULTISELECT — BaseUI
══════════════════════════════════════════════ */
[data-baseweb="select"] > div {{
    background-color: #1e293b !important;
    border-color: #475569 !important;
    color: #e2e8f0 !important;
}}
[data-baseweb="select"] svg {{
    fill: #94a3b8 !important;
}}
.stSelectbox > div > div,
.stMultiSelect > div > div {{
    background: #1e293b !important;
    color: #e2e8f0 !important;
    border: 1px solid #475569 !important;
}}

/* ══════════════════════════════════════════════
   DROPDOWN POPOVER & MENU
══════════════════════════════════════════════ */
[data-baseweb="popover"] {{
    background-color: #1e293b !important;
    border: 1px solid #334155 !important;
    border-radius: 8px !important;
    box-shadow: 0 8px 24px rgba(0,0,0,0.5) !important;
}}
[data-baseweb="menu"] {{
    background-color: #1e293b !important;
}}
[data-baseweb="menu"] ul {{
    background-color: #1e293b !important;
}}
[data-baseweb="menu"] li {{
    color: #e2e8f0 !important;
    background-color: #1e293b !important;
}}
[data-baseweb="menu"] li:hover {{
    background-color: #263040 !important;
}}
[data-baseweb="menu"] [aria-selected="true"] {{
    background-color: rgba(242,194,48,0.15) !important;
    color: {GOLD} !important;
}}

/* ══════════════════════════════════════════════
   MULTISELECT TAGS
══════════════════════════════════════════════ */
[data-baseweb="tag"] {{
    background: #334155 !important;
    color: #e2e8f0 !important;
    border-radius: 4px !important;
}}
[data-baseweb="tag"] span {{
    color: #e2e8f0 !important;
}}

/* ══════════════════════════════════════════════
   NUMBER INPUT
══════════════════════════════════════════════ */
[data-testid="stNumberInput"] input {{
    background: #1e293b !important;
    color: #e2e8f0 !important;
}}
[data-testid="stNumberInput"] button {{
    background: #1e293b !important;
    color: #e2e8f0 !important;
    border-color: #475569 !important;
}}

/* ══════════════════════════════════════════════
   DATE INPUT
══════════════════════════════════════════════ */
[data-testid="stDateInput"] input {{
    background: #1e293b !important;
    color: #e2e8f0 !important;
    border-color: #475569 !important;
}}
[data-baseweb="calendar"] {{
    background: #1e293b !important;
    border: 1px solid #334155 !important;
    border-radius: 8px !important;
}}
[data-baseweb="calendar"] * {{
    color: #e2e8f0 !important;
    background-color: transparent !important;
}}
[data-baseweb="calendar"] [aria-selected="true"] button,
[data-baseweb="calendar"] button[aria-selected="true"] {{
    background: {GOLD} !important;
    color: #111827 !important;
    border-radius: 50% !important;
}}
[data-baseweb="calendar"] button:hover {{
    background: rgba(242,194,48,0.2) !important;
}}
[data-baseweb="datepicker"] {{
    background: #1e293b !important;
}}

/* ══════════════════════════════════════════════
   CHECKBOXES & RADIOS (área principal)
══════════════════════════════════════════════ */
.stApp [data-testid="stCheckbox"] label span,
[data-testid="stMain"] [data-testid="stCheckbox"] label span {{
    color: #e2e8f0 !important;
}}
.stApp [data-testid="stRadio"] label,
[data-testid="stMain"] [data-testid="stRadio"] label {{
    color: #cbd5e1 !important;
}}

/* ══════════════════════════════════════════════
   METRIC CARDS
══════════════════════════════════════════════ */
[data-testid="metric-container"] {{
    background: #1e293b !important;
    border: 1px solid #334155 !important;
    border-radius: 10px !important;
    padding: 14px 18px !important;
}}
[data-testid="stMetricLabel"],
[data-testid="stMetricValue"],
[data-testid="stMetricDelta"] {{
    color: #e2e8f0 !important;
}}

/* ══════════════════════════════════════════════
   EXPANDERS
══════════════════════════════════════════════ */
[data-testid="stExpander"] {{
    background: #1e293b !important;
    border: 1px solid #334155 !important;
    border-radius: 8px !important;
}}
[data-testid="stExpander"] summary,
[data-testid="stExpander"] summary p,
[data-testid="stExpander"] p {{
    color: #e2e8f0 !important;
}}
[data-testid="stExpander"] summary:hover {{
    background: rgba(255,255,255,0.03) !important;
}}

/* ══════════════════════════════════════════════
   ALERTS
══════════════════════════════════════════════ */
[data-testid="stAlert"] {{
    border-radius: 8px !important;
}}
[data-testid="stAlert"] p,
[data-testid="stAlert"] span {{
    color: inherit !important;
}}
/* Info */
div[data-testid="stAlert"][kind="info"],
.stAlert.st-ae {{
    background: #1e3a5f !important;
    border-color: #3b82f6 !important;
    color: #bfdbfe !important;
}}
/* Success */
div[data-testid="stAlert"][kind="success"] {{
    background: #14532d !important;
    border-color: #22c55e !important;
    color: #bbf7d0 !important;
}}
/* Warning */
div[data-testid="stAlert"][kind="warning"] {{
    background: #451a03 !important;
    border-color: {GOLD} !important;
    color: #fde68a !important;
}}
/* Error */
div[data-testid="stAlert"][kind="error"] {{
    background: #450a0a !important;
    border-color: #ef4444 !important;
    color: #fecaca !important;
}}

/* ══════════════════════════════════════════════
   BORDERED CONTAINERS
══════════════════════════════════════════════ */
[data-testid="stVerticalBlockBorderWrapper"] {{
    background: #1e293b !important;
    border: 1px solid #334155 !important;
    border-radius: 10px !important;
}}

/* ══════════════════════════════════════════════
   DIALOG / MODAL
══════════════════════════════════════════════ */
[data-testid="stDialog"] > div {{
    background: #1e293b !important;
    border: 1px solid #334155 !important;
    border-radius: 12px !important;
    box-shadow: 0 20px 60px rgba(0,0,0,0.7) !important;
}}
[data-testid="stDialog"] h1,
[data-testid="stDialog"] h2,
[data-testid="stDialog"] h3,
[data-testid="stDialog"] p,
[data-testid="stDialog"] label,
[data-testid="stDialog"] span {{
    color: #e2e8f0 !important;
}}

/* ══════════════════════════════════════════════
   DATAFRAME / DATA EDITOR
   config.toml força base="light" → canvas sempre claro.
   filter: invert+hue-rotate inverte as cores para escuro no dark mode.
══════════════════════════════════════════════ */
[data-testid="stDataFrame"] {{
    border-radius: 8px !important;
    border: 1px solid #334155 !important;
    filter: invert(1) hue-rotate(180deg) !important;
}}
[data-testid="stDataEditor"] {{
    border: 1px solid #334155 !important;
    border-radius: 8px !important;
    filter: invert(1) hue-rotate(180deg) !important;
}}

/* ══════════════════════════════════════════════
   TABS
══════════════════════════════════════════════ */
[data-testid="stTabs"] {{
    background: transparent !important;
}}
[data-testid="stTabsContent"] {{
    background: transparent !important;
    border-top: 1px solid #334155 !important;
    padding-top: 16px !important;
}}
[data-testid="stTabs"] [role="tab"] {{
    color: #94a3b8 !important;
    border-bottom: 2px solid transparent !important;
    padding-bottom: 8px !important;
    font-size: 0.875rem !important;
    transition: color .15s;
}}
[data-testid="stTabs"] [role="tab"]:hover {{
    color: #e2e8f0 !important;
}}
[data-testid="stTabs"] [role="tab"][aria-selected="true"] {{
    color: {GOLD} !important;
    border-bottom-color: {GOLD} !important;
    font-weight: 600 !important;
}}

/* ══════════════════════════════════════════════
   POPOVER
══════════════════════════════════════════════ */
[data-testid="stPopover"] > div {{
    background: #1e293b !important;
    border: 1px solid #334155 !important;
    color: #e2e8f0 !important;
    border-radius: 8px !important;
}}

/* ══════════════════════════════════════════════
   BOTÕES
   Obs: com base="light" no config.toml o Streamlit injeta cor escura
   nos <p> filhos dos botões — precisamos sobrescrever explicitamente.
══════════════════════════════════════════════ */
[data-testid="stBaseButton-primary"],
.stApp button[kind="primary"] {{
    background: {GOLD} !important;
    color: #111827 !important;
    border: none !important;
    font-weight: 600 !important;
    border-radius: 6px !important;
}}
[data-testid="stBaseButton-primary"] p,
[data-testid="stBaseButton-primary"] span {{
    color: #111827 !important;
}}
[data-testid="stBaseButton-primary"]:hover,
.stApp button[kind="primary"]:hover {{
    background: #e0b020 !important;
    box-shadow: 0 4px 12px rgba(242,194,48,0.3) !important;
}}
[data-testid="stBaseButton-secondary"],
.stApp button[kind="secondary"] {{
    background: #1e293b !important;
    color: #e2e8f0 !important;
    border: 1px solid #475569 !important;
    border-radius: 6px !important;
}}
[data-testid="stBaseButton-secondary"] p,
[data-testid="stBaseButton-secondary"] span {{
    color: #e2e8f0 !important;
}}
[data-testid="stBaseButton-secondary"]:hover,
.stApp button[kind="secondary"]:hover {{
    border-color: {GOLD} !important;
    color: {GOLD} !important;
}}
[data-testid="stBaseButton-secondary"]:hover p,
[data-testid="stBaseButton-secondary"]:hover span {{
    color: {GOLD} !important;
}}
/* Popover button */
[data-testid="stPopover"] > div > button p,
[data-testid="stPopover"] > div > button span {{
    color: #e2e8f0 !important;
}}

/* ══════════════════════════════════════════════
   TOOLTIPS
══════════════════════════════════════════════ */
[data-baseweb="tooltip"] [role="tooltip"] {{
    background: #334155 !important;
    color: #e2e8f0 !important;
    border-radius: 6px !important;
    border: 1px solid #475569 !important;
}}

/* ══════════════════════════════════════════════
   TABELA CUSTOMIZADA (HTML)
══════════════════════════════════════════════ */
.team-header {{
    background: linear-gradient(90deg,#1a2e1a 0%,#2d4a2d 100%);
    border-left: 4px solid {GOLD};
    color: #fff !important;
    padding: 10px 16px;
    border-radius: 0 8px 8px 0;
    margin: 20px 0 4px 0;
    font-weight: 600;
    font-size: 1rem;
}}
.team-header-inactive {{
    background: linear-gradient(90deg,#2e1a1a 0%,#4a2d2d 100%);
    border-left: 4px solid #ef4444;
    color: #fff !important;
    padding: 10px 16px;
    border-radius: 0 8px 8px 0;
    margin: 20px 0 4px 0;
    font-weight: 600;
    font-size: 1rem;
}}
.tbl-equipe {{
    width: 100% !important; border-collapse: collapse !important; margin-bottom: 24px !important;
    font-size: 0.875rem !important; border-radius: 8px !important; overflow: hidden !important;
    box-shadow: 0 1px 3px rgba(0,0,0,.3) !important; background: transparent !important;
}}
.tbl-equipe thead tr {{ background: {SIDEBAR_BG} !important; }}
.tbl-equipe thead th {{ color: {GOLD} !important; font-weight: 600 !important; padding: 10px 12px !important; text-align: left !important; background: {SIDEBAR_BG} !important; }}
.tbl-equipe tbody tr {{ background: #0f172a !important; }}
.tbl-equipe tbody tr:nth-child(even) {{ background: #1e293b !important; }}
.tbl-equipe tbody tr:hover {{ background: #263040 !important; }}
.tbl-equipe th, .tbl-equipe td {{ padding: 9px 12px !important; border-bottom: 1px solid #334155 !important; white-space: nowrap !important; color: #e2e8f0 !important; }}
.tbl-wrapper {{ overflow-x: auto !important; margin-bottom: 20px !important; }}
/* stMarkdown não herda texto escuro sobre fundo escuro */
.stMarkdown table {{ background: transparent !important; }}
.stMarkdown td, .stMarkdown th {{ color: #e2e8f0 !important; background: transparent !important; }}
/* Flags */
.flag-red    {{ background:#2d1b1b !important; border-left: 3px solid #ef4444 !important; }}
.flag-yellow {{ background:#2d2b14 !important; border-left: 3px solid {GOLD} !important; }}
.flag-green  {{ background:#1b2d1f !important; border-left: 3px solid #22c55e !important; }}
</style>
"""

# ── CSS claro ────────────────────────────────────────────────────────────────
# Estratégia de especificidade:
#   • Widgets DENTRO do main area: [data-testid="stAppViewContainer"] como pai → (0,2,x)
#     garante que ganhe do dark CSS (0,1,x) mesmo que ambos estejam no DOM
#   • Widgets que renderizam em PORTAIS do body (popover, menu, calendar, dialog):
#     seletores nus (0,1,x) — dark CSS não está injetado no modo claro, então funcionam
_CSS_LIGHT = f"""
<style>
/* ══════════════════════════════════════════════
   SIDEBAR — sempre escura (idêntico ao dark mode)
══════════════════════════════════════════════ */
section[data-testid="stSidebar"] > div:first-child {{
    background-color: {SIDEBAR_BG} !important;
    padding: 0 !important;
    margin-top: 0 !important;
}}
[data-testid="stSidebarHeader"] {{
    display: none !important;
    height: 0 !important;
    min-height: 0 !important;
    padding: 0 !important;
    margin: 0 !important;
    overflow: hidden !important;
}}
[data-testid="stSidebarContent"] {{
    margin-top: -3.5rem !important;
    padding-top: 0 !important;
}}
[data-testid="stSidebarUserContent"] {{
    padding-top: 0 !important;
    margin-top: 0 !important;
}}
section[data-testid="stSidebar"] .block-container {{
    padding-top: 0 !important;
    margin-top: 0 !important;
}}
section[data-testid="stSidebar"] {{
    min-width: 240px !important;
    max-width: 240px !important;
}}
/* Textos brancos na sidebar */
section[data-testid="stSidebar"] label,
section[data-testid="stSidebar"] p,
section[data-testid="stSidebar"] span {{
    color: {TEXT_ACTIVE} !important;
}}
section[data-testid="stSidebar"] [data-testid="stRadio"] label {{
    color: {TEXT_MUTED} !important;
    font-size: 0.875rem;
    padding: 2px 0;
}}
section[data-testid="stSidebar"] [data-testid="stRadio"] label:has(input:checked) {{
    color: {TEXT_ACTIVE} !important;
    font-weight: 600;
}}
section[data-testid="stSidebar"] hr {{
    border-color: rgba(255,255,255,0.08) !important;
    margin: 6px 16px;
}}
/* Botões sidebar — sempre escuros (fundo explícito, transparent quebra com base="light") */
section[data-testid="stSidebar"] button,
section[data-testid="stSidebar"] [data-testid^="stBaseButton"],
section[data-testid="stSidebar"] [data-testid="stButton"] > button {{
    background: #1a2332 !important;
    background-color: #1a2332 !important;
    border: 1px solid rgba(255,255,255,0.12) !important;
    color: {TEXT_MUTED} !important;
    border-radius: 6px !important;
    font-size: 0.82rem !important;
    width: 100% !important;
    transition: all .15s ease;
}}
section[data-testid="stSidebar"] button:hover,
section[data-testid="stSidebar"] [data-testid^="stBaseButton"]:hover {{
    border-color: {GOLD} !important;
    color: {TEXT_ACTIVE} !important;
    background: rgba(242,194,48,0.08) !important;
    background-color: rgba(242,194,48,0.08) !important;
}}
section[data-testid="stSidebar"] button p,
section[data-testid="stSidebar"] button span,
section[data-testid="stSidebar"] [data-testid^="stBaseButton"] p,
section[data-testid="stSidebar"] [data-testid^="stBaseButton"] span {{
    color: {TEXT_MUTED} !important;
}}
/* Inputs sidebar — sempre escuros */
section[data-testid="stSidebar"] input,
section[data-testid="stSidebar"] [data-baseweb="input"],
section[data-testid="stSidebar"] [data-baseweb="base-input"],
section[data-testid="stSidebar"] [data-baseweb="input"] input,
section[data-testid="stSidebar"] [data-baseweb="base-input"] input {{
    background: #1e293b !important;
    background-color: #1e293b !important;
    color: #e2e8f0 !important;
    border-color: #475569 !important;
    caret-color: #e2e8f0 !important;
}}
/* Multiselect sidebar — sempre escuro */
section[data-testid="stSidebar"] [data-baseweb="select"] > div,
section[data-testid="stSidebar"] .stMultiSelect > div > div {{
    background: #1e293b !important;
    background-color: #1e293b !important;
    border-color: #475569 !important;
    color: #e2e8f0 !important;
}}
section[data-testid="stSidebar"] [data-baseweb="tag"] {{
    background: #334155 !important;
    background-color: #334155 !important;
    color: #e2e8f0 !important;
    border-radius: 4px !important;
}}
section[data-testid="stSidebar"] [data-baseweb="tag"] span,
section[data-testid="stSidebar"] [data-baseweb="tag"] button {{
    color: #e2e8f0 !important;
}}
/* Expander sidebar (ex: Salvar filtro atual) */
section[data-testid="stSidebar"] [data-testid="stExpander"] {{
    background: #1e293b !important;
    background-color: #1e293b !important;
    border: 1px solid #334155 !important;
    border-radius: 8px !important;
}}
section[data-testid="stSidebar"] [data-testid="stExpander"] summary,
section[data-testid="stSidebar"] [data-testid="stExpander"] summary p,
section[data-testid="stSidebar"] [data-testid="stExpander"] summary span {{
    color: #e2e8f0 !important;
    background: transparent !important;
}}
section[data-testid="stSidebar"] [data-testid="stExpander"] > div {{
    background: #1e293b !important;
    background-color: #1e293b !important;
}}

/* ══════════════════════════════════════════════
   CONTEÚDO PRINCIPAL — fundo e texto claros
══════════════════════════════════════════════ */
body,
.stApp,
[data-testid="stAppViewContainer"],
[data-testid="stMain"],
[data-testid="stMainBlockContainer"] {{
    background-color: #f8fafc !important;
    color: #1e293b !important;
}}
[data-testid="stAppViewContainer"] .block-container,
[data-testid="stMain"] .block-container {{
    background-color: #f8fafc !important;
    max-width: 100% !important;
}}
[data-testid="stAppViewContainer"] h1,
[data-testid="stAppViewContainer"] h2,
[data-testid="stAppViewContainer"] h3,
[data-testid="stAppViewContainer"] h4 {{
    color: #0f172a !important;
}}
[data-testid="stAppViewContainer"] p,
[data-testid="stAppViewContainer"] li,
[data-testid="stAppViewContainer"] label {{
    color: #334155 !important;
}}
[data-testid="stAppViewContainer"] hr {{
    border-color: #e2e8f0 !important;
}}

/* ══════════════════════════════════════════════
   LAYOUT GLOBAL
══════════════════════════════════════════════ */
#MainMenu, header[data-testid="stHeader"], footer, div[data-testid="stToolbar"] {{
    display: none !important;
}}
[data-testid="stBaseButton-headerNoPadding"],
button[data-testid="baseButton-headerNoPadding"],
[data-testid="stSidebarCollapseButton"],
[data-testid="collapsedControl"] {{
    display: none !important;
}}
[data-testid="stPopover"] > div > button svg {{
    display: none !important;
}}
.block-container,
[data-testid="stMainBlockContainer"],
[data-testid="stMain"] > div:first-child {{
    padding-top: 0 !important;
    padding-bottom: 1rem !important;
    max-width: 100% !important;
}}

/* ══════════════════════════════════════════════
   BOTÕES — LIGHT
══════════════════════════════════════════════ */
[data-testid="stBaseButton-primary"] {{
    background: {GOLD} !important;
    color: #111827 !important;
    border: none !important;
    font-weight: 600 !important;
    border-radius: 6px !important;
}}
[data-testid="stBaseButton-primary"]:hover {{
    background: #e0b020 !important;
    box-shadow: 0 2px 8px rgba(242,194,48,.35) !important;
}}
[data-testid="stAppViewContainer"] [data-testid="stBaseButton-secondary"] {{
    background: #ffffff !important;
    color: #1e293b !important;
    border: 1px solid #cbd5e1 !important;
    border-radius: 6px !important;
}}
[data-testid="stAppViewContainer"] [data-testid="stBaseButton-secondary"]:hover {{
    border-color: #1e40af !important;
    color: #1e40af !important;
}}

/* ══════════════════════════════════════════════
   INPUTS — LIGHT
══════════════════════════════════════════════ */
[data-testid="stAppViewContainer"] [data-baseweb="input"],
[data-testid="stAppViewContainer"] [data-baseweb="base-input"] {{
    background-color: #ffffff !important;
    border-color: #cbd5e1 !important;
}}
[data-testid="stAppViewContainer"] [data-baseweb="input"] input,
[data-testid="stAppViewContainer"] [data-baseweb="base-input"] input,
[data-testid="stAppViewContainer"] .stTextInput input,
[data-testid="stAppViewContainer"] .stNumberInput input {{
    background: #ffffff !important;
    color: #1e293b !important;
    border: 1px solid #cbd5e1 !important;
    caret-color: #1e293b !important;
}}
[data-testid="stAppViewContainer"] [data-baseweb="textarea"] textarea,
[data-testid="stAppViewContainer"] .stTextArea textarea {{
    background-color: #ffffff !important;
    color: #1e293b !important;
    border-color: #cbd5e1 !important;
}}
[data-testid="stAppViewContainer"] [data-testid="stNumberInput"] button {{
    background: #ffffff !important;
    color: #1e293b !important;
    border-color: #cbd5e1 !important;
}}

/* ══════════════════════════════════════════════
   SELECT / MULTISELECT — LIGHT
══════════════════════════════════════════════ */
[data-testid="stAppViewContainer"] [data-baseweb="select"] > div,
[data-testid="stAppViewContainer"] .stSelectbox > div > div,
[data-testid="stAppViewContainer"] .stMultiSelect > div > div {{
    background-color: #ffffff !important;
    color: #1e293b !important;
    border-color: #cbd5e1 !important;
}}
[data-testid="stAppViewContainer"] [data-baseweb="select"] svg {{
    fill: #64748b !important;
}}
[data-testid="stAppViewContainer"] [data-baseweb="tag"] {{
    background: #e2e8f0 !important;
    color: #1e293b !important;
}}
[data-testid="stAppViewContainer"] [data-baseweb="tag"] span {{
    color: #1e293b !important;
}}

/* ══════════════════════════════════════════════
   POPOVER & MENU (portais body-level) — LIGHT
══════════════════════════════════════════════ */
[data-baseweb="popover"] {{
    background-color: #ffffff !important;
    border: 1px solid #e2e8f0 !important;
    border-radius: 8px !important;
    box-shadow: 0 4px 16px rgba(0,0,0,.12) !important;
}}
[data-baseweb="menu"],
[data-baseweb="menu"] ul {{
    background-color: #ffffff !important;
}}
[data-baseweb="menu"] li {{
    color: #1e293b !important;
    background-color: #ffffff !important;
}}
[data-baseweb="menu"] li:hover {{
    background-color: #f1f5f9 !important;
}}
[data-baseweb="menu"] [aria-selected="true"] {{
    background-color: #eff6ff !important;
    color: #1e40af !important;
}}

/* ══════════════════════════════════════════════
   FORMULÁRIOS / CONTAINERS / EXPANDERS — LIGHT
══════════════════════════════════════════════ */
[data-testid="stAppViewContainer"] [data-testid="stForm"] {{
    background: #ffffff !important;
    border: 1px solid #e2e8f0 !important;
    border-radius: 10px !important;
    padding: 20px !important;
}}
[data-testid="stAppViewContainer"] [data-testid="stVerticalBlockBorderWrapper"] {{
    background: #ffffff !important;
    border: 1px solid #e2e8f0 !important;
    border-radius: 10px !important;
}}
[data-testid="stAppViewContainer"] [data-testid="stExpander"] {{
    background: #ffffff !important;
    border: 1px solid #e2e8f0 !important;
    border-radius: 8px !important;
}}
[data-testid="stAppViewContainer"] [data-testid="stExpander"] summary,
[data-testid="stAppViewContainer"] [data-testid="stExpander"] summary p {{
    color: #1e293b !important;
}}

/* ══════════════════════════════════════════════
   DIALOG / MODAL (portal body-level) — LIGHT
══════════════════════════════════════════════ */
[data-testid="stDialog"] > div {{
    background: #ffffff !important;
    border: 1px solid #e2e8f0 !important;
    border-radius: 12px !important;
    box-shadow: 0 20px 60px rgba(0,0,0,.15) !important;
}}
[data-testid="stDialog"] h1,
[data-testid="stDialog"] h2,
[data-testid="stDialog"] h3,
[data-testid="stDialog"] p,
[data-testid="stDialog"] label {{ color: #1e293b !important; }}
[data-testid="stDialog"] [data-baseweb="input"] input,
[data-testid="stDialog"] [data-baseweb="base-input"] input {{
    background-color: #ffffff !important;
    color: #1e293b !important;
}}
[data-testid="stDialog"] [data-baseweb="select"] > div {{
    background-color: #ffffff !important;
    color: #1e293b !important;
    border-color: #cbd5e1 !important;
}}

/* ══════════════════════════════════════════════
   TABS — LIGHT
══════════════════════════════════════════════ */
[data-testid="stAppViewContainer"] [data-testid="stTabsContent"] {{
    border-top: 1px solid #e2e8f0 !important;
    padding-top: 16px !important;
}}
[data-testid="stAppViewContainer"] [data-testid="stTabs"] [role="tab"] {{
    color: #64748b !important;
}}
[data-testid="stAppViewContainer"] [data-testid="stTabs"] [role="tab"][aria-selected="true"] {{
    color: #1e40af !important;
    border-bottom-color: #1e40af !important;
    font-weight: 600 !important;
}}

/* ══════════════════════════════════════════════
   ALERTS — LIGHT
══════════════════════════════════════════════ */
[data-testid="stAppViewContainer"] div[data-testid="stAlert"][kind="info"] {{
    background: #eff6ff !important; border-color: #3b82f6 !important; color: #1e40af !important;
}}
[data-testid="stAppViewContainer"] div[data-testid="stAlert"][kind="success"] {{
    background: #f0fdf4 !important; border-color: #22c55e !important; color: #15803d !important;
}}
[data-testid="stAppViewContainer"] div[data-testid="stAlert"][kind="warning"] {{
    background: #fefce8 !important; border-color: {GOLD} !important; color: #92400e !important;
}}
[data-testid="stAppViewContainer"] div[data-testid="stAlert"][kind="error"] {{
    background: #fef2f2 !important; border-color: #ef4444 !important; color: #991b1b !important;
}}
[data-testid="stAppViewContainer"] [data-testid="stAlert"] p,
[data-testid="stAppViewContainer"] [data-testid="stAlert"] span {{ color: inherit !important; }}

/* ══════════════════════════════════════════════
   TABELA HTML CUSTOMIZADA — LIGHT
══════════════════════════════════════════════ */
.team-header {{
    background: linear-gradient(90deg,#e8f5e9 0%,#c8e6c9 100%) !important;
    border-left: 4px solid {GOLD} !important;
    color: #1b3a1b !important;
    padding: 10px 16px !important;
    border-radius: 0 8px 8px 0 !important;
    margin: 20px 0 4px 0 !important;
    font-weight: 600 !important;
    font-size: 1rem !important;
}}
.team-header-inactive {{
    background: linear-gradient(90deg,#fce4e4 0%,#f8c8c8 100%) !important;
    border-left: 4px solid #ef4444 !important;
    color: #5a1a1a !important;
    padding: 10px 16px !important;
    border-radius: 0 8px 8px 0 !important;
    margin: 20px 0 4px 0 !important;
    font-weight: 600 !important;
    font-size: 1rem !important;
}}
.tbl-equipe {{
    width: 100% !important; border-collapse: collapse !important;
    margin-bottom: 24px !important; font-size: 0.875rem !important;
    border-radius: 8px !important; overflow: hidden !important;
    box-shadow: 0 1px 3px rgba(0,0,0,.08) !important;
    background: transparent !important;
}}
.tbl-equipe thead tr {{ background: #e2e8f0 !important; }}
.tbl-equipe thead th {{
    color: #0f172a !important; font-weight: 700 !important;
    padding: 10px 12px !important; text-align: left !important;
    background: #e2e8f0 !important;
}}
.tbl-equipe tbody tr {{ background: #ffffff !important; }}
.tbl-equipe tbody tr:nth-child(even) {{ background: #f8fafc !important; }}
.tbl-equipe tbody tr:hover {{ background: #e2e8f0 !important; }}
.tbl-equipe th, .tbl-equipe td {{
    padding: 9px 12px !important; border-bottom: 1px solid #e2e8f0 !important;
    white-space: nowrap !important; color: #1e293b !important;
}}
.tbl-wrapper {{ overflow-x: auto !important; margin-bottom: 20px !important; }}
.stMarkdown table {{ background: transparent !important; }}
.stMarkdown td, .stMarkdown th {{ color: #1e293b !important; background: transparent !important; }}
.flag-red    {{ background:#fef2f2 !important; border-left: 3px solid #ef4444 !important; }}
.flag-yellow {{ background:#fefce8 !important; border-left: 3px solid {GOLD} !important; }}
.flag-green  {{ background:#f0fdf4 !important; border-left: 3px solid #22c55e !important; }}
</style>
"""


def _inject_css() -> None:
    """Injeta CSS. Na primeira execução da sessão (após F5) lê o tema de
    st.query_params['theme'] — o Streamlit popula query_params a partir da
    URL da requisição, que inclui ?theme=light quando o usuário estava em
    modo claro antes do F5.
    """
    if "color_mode" not in st.session_state:
        param = st.query_params.get("theme", "dark")
        st.session_state["color_mode"] = param if param in ("light", "dark") else "dark"
    mode = st.session_state["color_mode"]
    css = _CSS_DARK if mode == "dark" else _CSS_LIGHT
    st.markdown(css, unsafe_allow_html=True)


def render_sidebar(user: dict, current_page: str) -> dict:
    """
    Renderiza a sidebar Prosper. Retorna dict com as seleções:
    {modo, segmento, pagina, logout_clicked, agrupar_por}
    """
    _inject_css()

    with st.sidebar:
        # ── Logo + título (idêntico ao estilo Chamados) ──────────────────────
        logo_path = Path("assets/logo.png")
        if logo_path.exists():
            logo_b64 = base64.b64encode(logo_path.read_bytes()).decode()
            st.markdown(
                f"""
                <div style="padding:14px 16px 10px;display:flex;align-items:center;gap:10px;">
                    <img src="data:image/png;base64,{logo_b64}"
                         style="width:32px;height:32px;border-radius:50%;object-fit:cover;
                                flex-shrink:0;" />
                    <div style="line-height:1.2;">
                        <div style="color:#fff;font-weight:700;font-size:0.9rem;">Gerenciamento</div>
                        <div style="color:#fff;font-weight:700;font-size:0.9rem;">de Telefones</div>
                    </div>
                </div>
                """,
                unsafe_allow_html=True,
            )
        else:
            st.markdown(
                f"""
                <div style="padding:14px 16px 10px;display:flex;align-items:center;gap:10px;">
                    <div style="width:34px;height:34px;border-radius:50%;background:{GOLD};
                                display:flex;align-items:center;justify-content:center;
                                font-size:1.1rem;font-weight:900;color:#111827;flex-shrink:0;">P</div>
                    <div style="line-height:1.2;">
                        <div style="color:#fff;font-weight:700;font-size:0.9rem;">Gerenciamento</div>
                        <div style="color:#fff;font-weight:700;font-size:0.9rem;">de Telefones</div>
                    </div>
                </div>
                """,
                unsafe_allow_html=True,
            )

        # ── Navegação de páginas (logo abaixo do título) ─────────────────────
        pagina = current_page
        if st.button("📋 Painel de Linhas", use_container_width=True, key="btn_painel"):
            pagina = "painel"

        if user.get("is_admin") or user.get("role") == "admin":
            if st.button("⚙️ Config & Admin", use_container_width=True, key="btn_admin"):
                pagina = "config"

        st.divider()

        # ── Modo de visualização ─────────────────────────────────────────────
        st.markdown(
            '<p style="color:rgba(255,255,255,0.65);font-size:0.68rem;text-transform:uppercase;'
            'letter-spacing:.08em;margin:4px 0 2px 0;padding-left:4px;">Modo</p>',
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

        # ── Segmento ─────────────────────────────────────────────────────────
        st.markdown(
            '<p style="color:rgba(255,255,255,0.65);font-size:0.68rem;text-transform:uppercase;'
            'letter-spacing:.08em;margin:4px 0 2px 0;padding-left:4px;">Segmento</p>',
            unsafe_allow_html=True,
        )
        seg_default = st.session_state.get("nav_segmento", "Alimento")
        if seg_default not in SEGMENTOS:
            seg_default = "Alimento"
        segmento = st.radio(
            "segmento",
            SEGMENTOS,
            index=SEGMENTOS.index(seg_default),
            key="sidebar_segmento",
            label_visibility="collapsed",
        )

        st.divider()

        # ── Agrupar por ──────────────────────────────────────────────────────
        st.markdown(
            '<p style="color:rgba(255,255,255,0.65);font-size:0.68rem;text-transform:uppercase;'
            'letter-spacing:.08em;margin:4px 0 2px 0;padding-left:4px;">Agrupar por</p>',
            unsafe_allow_html=True,
        )
        _agrupar_opts = ["Equipe", "Setor", "Gestor", "Cargo"]
        _agrupar_default = st.session_state.get("sidebar_agrupar_por", "Equipe")
        if _agrupar_default not in _agrupar_opts:
            _agrupar_default = "Equipe"
        agrupar_por = st.radio(
            "agrupar_por",
            _agrupar_opts,
            index=_agrupar_opts.index(_agrupar_default),
            key="sidebar_agrupar_por",
            label_visibility="collapsed",
        )

        # ── Rodapé: usuário + toggle modo + logout (estilo Chamados) ─────────
        st.markdown('<div style="flex:1;"></div>', unsafe_allow_html=True)
        st.divider()

        username  = user.get("username") or user.get("email") or "Usuário"
        is_admin  = user.get("is_admin") or user.get("role") == "admin"
        role_label = "Administrador" if is_admin else "Técnico"
        initial   = username[0].upper() if username else "U"

        is_dark = st.session_state.get("color_mode", "dark") == "dark"
        toggle_icon = "☀️" if is_dark else "🌙"

        st.markdown(
            f"""
            <div style="display:flex;align-items:center;gap:10px;padding:8px 4px 4px;">
                <div style="width:36px;height:36px;border-radius:50%;background:{GOLD};
                            display:flex;align-items:center;justify-content:center;
                            font-size:0.95rem;font-weight:700;color:#111827;flex-shrink:0;">
                    {initial}
                </div>
                <div style="flex:1;min-width:0;">
                    <div style="color:#fff;font-size:0.8rem;font-weight:600;
                                white-space:nowrap;overflow:hidden;text-overflow:ellipsis;">
                        {username}
                    </div>
                    <div style="color:rgba(255,255,255,0.45);font-size:0.7rem;">{role_label}</div>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        _c1, _c2 = st.columns([1, 1])
        with _c1:
            if st.button(toggle_icon, use_container_width=True, key="btn_toggle_mode",
                         help="Alternar modo claro/escuro"):
                new_mode = "light" if is_dark else "dark"
                st.session_state["color_mode"] = new_mode
                st.query_params["theme"] = new_mode
                st.rerun()
        with _c2:
            logout_clicked = st.button("↪ Sair", use_container_width=True, key="sidebar_logout")

    return {
        "modo":           modo,
        "segmento":       segmento,
        "pagina":         pagina,
        "logout_clicked": logout_clicked,
        "agrupar_por":    agrupar_por,
    }


def render_column_picker(all_cols: list, visible_cols: list) -> list:
    """
    Renderiza multiselect na sidebar para ocultar/mostrar colunas.
    Retorna lista de colunas selecionadas (nunca vazia).
    """
    with st.sidebar:
        st.divider()
        st.markdown(
            '<p style="color:rgba(255,255,255,0.65);font-size:0.68rem;text-transform:uppercase;'
            'letter-spacing:.08em;margin:4px 0 2px 0;padding-left:4px;">Colunas visíveis</p>',
            unsafe_allow_html=True,
        )
        selected = st.multiselect(
            "cols",
            options=all_cols,
            default=[c for c in visible_cols if c in all_cols],
            key="sidebar_col_picker",
            label_visibility="collapsed",
        )
        return selected if selected else visible_cols
