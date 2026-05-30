"""Componente de filtros salvos — renderiza na sidebar."""
from __future__ import annotations
import streamlit as st


def render_filtros_salvos(
    usuario_id: int,
    filtros: list,
    on_aplicar,
    on_excluir,
) -> None:
    """
    Renderiza seção de filtros salvos na sidebar.
    on_aplicar(filtro: dict) -> None
    on_excluir(filtro_id: int) -> None
    """
    with st.sidebar:
        st.divider()
        st.markdown(
            '<p style="color:rgba(255,255,255,0.4);font-size:0.68rem;text-transform:uppercase;'
            'letter-spacing:.08em;margin:4px 0 2px 0;padding-left:4px;">Filtros salvos</p>',
            unsafe_allow_html=True,
        )
        if not filtros:
            st.markdown(
                '<span style="color:rgba(255,255,255,0.35);font-size:0.78rem;">Nenhum filtro salvo.</span>',
                unsafe_allow_html=True,
            )
        else:
            for f in filtros:
                col_a, col_b = st.columns([4, 1])
                with col_a:
                    if st.button(f["nome"], key=f"filtro_apply_{f['id']}", use_container_width=True):
                        on_aplicar(f["filtro"])
                        st.rerun()
                with col_b:
                    if st.button("✕", key=f"filtro_del_{f['id']}"):
                        on_excluir(f["id"])
                        st.rerun()


def render_salvar_filtro_atual(filtro_atual: dict, on_salvar) -> None:
    """Formulário inline na sidebar para salvar o filtro atual com um nome."""
    with st.sidebar:
        with st.expander("💾 Salvar filtro atual", expanded=False):
            nome = st.text_input(
                "Nome do filtro",
                key="novo_filtro_nome",
                placeholder="Ex.: Vendedores Baixada",
                label_visibility="collapsed",
            )
            if st.button("Salvar", key="btn_salvar_filtro", use_container_width=True) and nome.strip():
                on_salvar(nome.strip(), filtro_atual)
                st.success(f"Filtro '{nome}' salvo!")
                st.rerun()
