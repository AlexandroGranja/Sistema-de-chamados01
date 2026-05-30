"""Página de administração: equipes, gestores, usuários unificados, auditoria."""
from __future__ import annotations
import streamlit as st
import pandas as pd

SEGMENTOS = ["Alimento", "Medicamento", "Promotores", "Internos", "Manutenção", "Roubo e Perda"]


def render_config_admin() -> None:
    st.title("⚙️ Configurações & Administração")
    tab_gest_eq, tab_gestores, tab_equipes, tab_usuarios, tab_auditoria = st.tabs([
        "🏢 Gestores & Equipes",
        "👤 Gestores",
        "📂 Equipes",
        "🔑 Usuários",
        "📋 Auditoria",
    ])
    with tab_gest_eq:
        _render_gestores_equipes()
    with tab_gestores:
        _render_gestores()
    with tab_equipes:
        _render_equipes()
    with tab_usuarios:
        _render_usuarios()
    with tab_auditoria:
        _render_auditoria()


# ── Gestores & Equipes (edição rápida) ───────────────────────────────────────

def _render_gestores_equipes() -> None:
    """Data editor das equipes reais com Gestor e Supervisor editáveis."""
    try:
        from src.db.repository import listar_equipes_da_tabela, atualizar_gestor_equipe, criar_equipe_na_tabela
    except ImportError:
        st.error("Módulo de banco indisponível.")
        return

    equipes = listar_equipes_da_tabela()
    st.subheader("Editar Gestor e Supervisor por equipe")
    st.caption("Altere os campos Gestor e Supervisor diretamente na tabela e clique em Salvar.")

    if not equipes:
        st.info("Nenhuma equipe encontrada.")
    else:
        df = pd.DataFrame(equipes)[["equipe", "segmento", "gestor", "supervisor"]]
        df.columns = ["Equipe", "Segmento", "Gestor", "Supervisor"]
        edited = st.data_editor(
            df, hide_index=True, use_container_width=True, num_rows="fixed",
            column_config={
                "Equipe":     st.column_config.TextColumn("Equipe",     disabled=True),
                "Segmento":   st.column_config.TextColumn("Segmento",   disabled=True),
                "Gestor":     st.column_config.TextColumn("Gestor",     max_chars=255),
                "Supervisor": st.column_config.TextColumn("Supervisor", max_chars=255),
            },
            key="editor_gest_eq",
        )
        if st.button("💾 Salvar alterações", type="primary", key="btn_save_gest_eq"):
            saved, errors = 0, []
            for _, row in edited.iterrows():
                orig = next((e for e in equipes if e["equipe"] == row["Equipe"]), None)
                if orig and (row["Gestor"] != orig["gestor"] or row["Supervisor"] != orig["supervisor"]):
                    try:
                        n = atualizar_gestor_equipe(row["Equipe"], row["Gestor"], row["Supervisor"])
                        if n > 0:
                            saved += 1
                    except Exception as exc:
                        errors.append(f"{row['Equipe']}: {exc}")
            if errors:
                st.error("Erros: " + " | ".join(errors))
            elif saved:
                st.success(f"{saved} equipe(s) atualizada(s)!")
                st.rerun()
            else:
                st.info("Nenhuma alteração detectada.")

    st.divider()
    st.subheader("Criar nova equipe")
    c1, c2, c3, c4 = st.columns(4)
    with c1:
        nova_eq = st.text_input("Nome da equipe *", key="nova_eq_nome")
    with c2:
        nova_seg = st.selectbox("Segmento *", SEGMENTOS, key="nova_eq_seg")
    with c3:
        nova_gest = st.text_input("Gestor", key="nova_eq_gest")
    with c4:
        nova_sup = st.text_input("Supervisor", key="nova_eq_sup")
    if st.button("➕ Criar equipe", type="primary", key="btn_criar_eq"):
        if not nova_eq.strip():
            st.warning("Nome da equipe é obrigatório.")
        else:
            ok = criar_equipe_na_tabela(nova_eq.strip(), nova_seg, nova_gest.strip(), nova_sup.strip())
            if ok:
                st.success(f"Equipe '{nova_eq}' criada!")
                st.rerun()
            else:
                st.warning(f"Equipe '{nova_eq}' já existe.")


# ── Gestores ─────────────────────────────────────────────────────────────────

def _render_gestores() -> None:
    """Lista gestores reais do banco, permite renomear e criar novo."""
    try:
        from src.db.repository import listar_gestores_da_tabela, renomear_gestor, atualizar_gestor_equipe
    except ImportError:
        st.error("Módulo de banco indisponível.")
        return

    gestores = listar_gestores_da_tabela()

    st.subheader("Gestores cadastrados")
    if gestores:
        df = pd.DataFrame(gestores)
        df.columns = ["Gestor", "Nº Equipes", "Equipes"]
        st.dataframe(df, hide_index=True, use_container_width=True)
    else:
        st.info("Nenhum gestor encontrado na base de dados.")

    st.divider()
    st.subheader("Renomear gestor")
    st.caption("Altera o nome do gestor em todas as linhas onde ele aparece.")
    if gestores:
        nomes = [g["gestor"] for g in gestores]
        g_sel = st.selectbox("Selecione o gestor", nomes, key="gest_renomear_sel")
        novo_nome = st.text_input("Novo nome", value=g_sel, key="gest_renomear_novo")
        if st.button("Renomear", type="primary", key="btn_renomear_gest"):
            if novo_nome.strip() and novo_nome.strip() != g_sel:
                n = renomear_gestor(g_sel, novo_nome.strip())
                if n:
                    st.success(f"'{g_sel}' renomeado para '{novo_nome}' em {n} linha(s).")
                    st.rerun()
                else:
                    st.warning("Nenhuma linha alterada.")
            elif novo_nome.strip() == g_sel:
                st.info("O nome não foi alterado.")
            else:
                st.warning("Informe o novo nome.")

    st.divider()
    st.subheader("Adicionar gestor a uma equipe")
    st.caption("Define o gestor de uma equipe específica.")
    try:
        from src.db.repository import listar_equipes_da_tabela
        equipes = listar_equipes_da_tabela()
        if equipes:
            eq_nomes = [e["equipe"] for e in equipes]
            eq_sel = st.selectbox("Equipe", eq_nomes, key="gest_add_eq_sel")
            eq_obj = next((e for e in equipes if e["equipe"] == eq_sel), {})
            novo_gest = st.text_input("Novo gestor", value=eq_obj.get("gestor", ""), key="gest_add_nome")
            novo_sup = st.text_input("Supervisor (opcional)", value=eq_obj.get("supervisor", ""), key="gest_add_sup")
            if st.button("Salvar", type="primary", key="btn_gest_add_save"):
                n = atualizar_gestor_equipe(eq_sel, novo_gest, novo_sup)
                if n:
                    st.success(f"Gestor atualizado em {n} linha(s) da equipe '{eq_sel}'.")
                    st.rerun()
    except Exception:
        pass


# ── Equipes ───────────────────────────────────────────────────────────────────

def _render_equipes() -> None:
    """Lista equipes reais do banco, permite renomear, desativar, excluir e criar."""
    try:
        from src.db.repository import (
            listar_equipes_da_tabela, renomear_equipe,
            desativar_equipe, excluir_equipe, contar_linhas_equipe,
            criar_equipe_na_tabela,
        )
    except ImportError:
        st.error("Módulo de banco indisponível.")
        return

    equipes = listar_equipes_da_tabela()

    # ── Tabela de equipes ────────────────────────────────────────────────────
    st.subheader("Equipes cadastradas")
    if equipes:
        df = pd.DataFrame(equipes)[["equipe", "segmento", "gestor", "supervisor"]]
        df.columns = ["Equipe", "Segmento", "Gestor", "Supervisor"]
        st.dataframe(df, hide_index=True, use_container_width=True)
    else:
        st.info("Nenhuma equipe encontrada na base de dados.")
        equipes = []

    if equipes:
        nomes_eq = [e["equipe"] for e in equipes]

        # ── Renomear ─────────────────────────────────────────────────────────
        st.divider()
        st.subheader("Renomear equipe")
        st.caption("Atualiza o nome em todas as linhas da equipe.")
        c1, c2, c3 = st.columns([2, 2, 1])
        with c1:
            eq_ren = st.selectbox("Equipe", nomes_eq, key="eq_ren_sel")
        with c2:
            novo_nome_eq = st.text_input("Novo nome", value=eq_ren, key="eq_ren_novo")
        with c3:
            st.markdown("<div style='margin-top:28px'></div>", unsafe_allow_html=True)
            if st.button("Renomear", type="primary", key="btn_ren_eq", use_container_width=True):
                if novo_nome_eq.strip() and novo_nome_eq.strip() != eq_ren:
                    n = renomear_equipe(eq_ren, novo_nome_eq.strip())
                    st.success(f"'{eq_ren}' → '{novo_nome_eq}' em {n} linha(s).") if n else st.warning("Nenhuma linha alterada.")
                    if n:
                        st.rerun()
                elif novo_nome_eq.strip() == eq_ren:
                    st.info("Nome não foi alterado.")
                else:
                    st.warning("Informe o novo nome.")

        # ── Desativar / Excluir ──────────────────────────────────────────────
        st.divider()
        st.subheader("Desativar ou excluir equipe")

        c1, c2 = st.columns([3, 2])
        with c1:
            eq_acao = st.selectbox("Selecione a equipe", nomes_eq, key="eq_acao_sel")
        with c2:
            contagem = contar_linhas_equipe(eq_acao)
            st.metric("Linhas ativas", contagem["ativas"])

        st.caption(
            f"**Desativar**: move as {contagem['ativas']} linha(s) ativa(s) para desativadas — podem ser reativadas. "
            f"**Excluir**: apaga permanentemente todas as {contagem['ativas'] + contagem['desativadas']} linha(s) da equipe."
        )

        c_des, c_exc = st.columns(2)
        with c_des:
            if st.button("⏸ Desativar equipe", key="btn_desativar_eq", use_container_width=True, disabled=contagem["ativas"] == 0):
                n = desativar_equipe(eq_acao)
                st.success(f"{n} linha(s) de '{eq_acao}' movida(s) para desativadas.") if n else st.info("Nenhuma linha ativa encontrada.")
                if n:
                    st.rerun()
        with c_exc:
            total = contagem["ativas"] + contagem["desativadas"]
            if "confirmar_excluir_eq" not in st.session_state:
                st.session_state["confirmar_excluir_eq"] = False

            if not st.session_state["confirmar_excluir_eq"]:
                if st.button("🗑 Excluir equipe", key="btn_excluir_eq_init", use_container_width=True, type="secondary"):
                    st.session_state["confirmar_excluir_eq"] = True
                    st.rerun()
            else:
                st.warning(f"Isso vai excluir **{total} linha(s)** permanentemente. Confirma?")
                cc1, cc2 = st.columns(2)
                with cc1:
                    if st.button("✅ Confirmar exclusão", key="btn_excluir_eq_confirm", type="primary", use_container_width=True):
                        n = excluir_equipe(eq_acao)
                        st.session_state["confirmar_excluir_eq"] = False
                        st.success(f"{n} linha(s) de '{eq_acao}' excluída(s).")
                        st.rerun()
                with cc2:
                    if st.button("Cancelar", key="btn_excluir_eq_cancel", use_container_width=True):
                        st.session_state["confirmar_excluir_eq"] = False
                        st.rerun()

    # ── Criar nova equipe ────────────────────────────────────────────────────
    st.divider()
    st.subheader("Criar nova equipe")
    c1, c2, c3, c4 = st.columns(4)
    with c1:
        ne = st.text_input("Nome *", key="eq_nova_nome")
    with c2:
        ns = st.selectbox("Segmento *", SEGMENTOS, key="eq_nova_seg")
    with c3:
        ng = st.text_input("Gestor", key="eq_nova_gest")
    with c4:
        nsup = st.text_input("Supervisor", key="eq_nova_sup")
    if st.button("➕ Criar equipe", type="primary", key="btn_eq_nova_criar"):
        if not ne.strip():
            st.warning("Nome é obrigatório.")
        else:
            ok = criar_equipe_na_tabela(ne.strip(), ns, ng.strip(), nsup.strip())
            if ok:
                st.success(f"Equipe '{ne}' criada!")
                st.rerun()
            else:
                st.warning(f"Equipe '{ne}' já existe.")


# ── Usuários unificados ───────────────────────────────────────────────────────

def _render_usuarios() -> None:
    """Lista e gerencia usuários de ambos os sistemas (Gerenciamento + Chamados)."""
    if not (st.session_state.get("user") or {}).get("is_admin"):
        st.info("Apenas administradores podem gerenciar usuários.")
        return

    try:
        from src.db.repository import (
            listar_usuarios_unificado, criar_usuario_unificado,
            atualizar_senha_unificada, alternar_admin_unificado,
            desativar_usuario_unificado, excluir_usuario_unificado,
        )
    except ImportError:
        st.error("Módulo de banco indisponível.")
        return

    usuarios = listar_usuarios_unificado()

    st.subheader("Usuários dos dois sistemas")
    st.caption("Usuários cadastrados no Gerenciamento de Telefones e/ou no Sistema de Chamados.")

    if usuarios:
        rows = []
        for u in usuarios:
            rows.append({
                "Usuário":       u.get("username") or u.get("name_chamados") or "—",
                "E-mail":        u.get("email_gerenc") or u.get("email_chamados") or "—",
                "Admin (Gerenc)": "✅" if u.get("admin_gerenc") else "—",
                "Role (Chamados)": u.get("role_chamados") or "—",
                "Gerenciamento": "✅" if u.get("id_gerenc") else "❌",
                "Chamados":      "✅" if u.get("id_chamados") else "❌",
                "Ativo":         "✅" if (u.get("ativo_gerenc") and u.get("ativo_chamados") is not False) else "⚠️",
            })
        st.dataframe(pd.DataFrame(rows), hide_index=True, use_container_width=True)

    st.divider()
    st.subheader("Criar novo usuário")
    st.caption("Cria o usuário em ambos os sistemas simultaneamente.")
    c1, c2 = st.columns(2)
    with c1:
        nu = st.text_input("Nome / usuário *", key="uni_new_user")
        ne = st.text_input("E-mail", key="uni_new_email")
    with c2:
        np1 = st.text_input("Senha *", type="password", key="uni_new_pass1")
        np2 = st.text_input("Confirmar senha *", type="password", key="uni_new_pass2")
    is_adm = st.checkbox("Administrador (ambos os sistemas)", key="uni_new_admin")

    if st.button("Criar usuário", type="primary", key="uni_btn_criar"):
        if not nu.strip():
            st.warning("Nome/usuário é obrigatório.")
        elif len(np1) < 8:
            st.error("Senha deve ter ao menos 8 caracteres.")
        elif np1 != np2:
            st.error("As senhas não conferem.")
        else:
            res = criar_usuario_unificado(nu.strip(), ne.strip(), np1, is_adm)
            partes = []
            if res["gerenc"]:
                partes.append("Gerenciamento ✅")
            if res["chamados"]:
                partes.append("Chamados ✅")
            if partes:
                st.success(f"Usuário '{nu}' criado em: {', '.join(partes)}")
                st.rerun()
            else:
                st.error("Não foi possível criar o usuário (já existe ou erro de banco).")

    st.divider()
    st.subheader("Alterar senha")
    st.caption("Atualiza a senha em ambos os sistemas.")
    if usuarios:
        nomes = list({u.get("username") or u.get("name_chamados") for u in usuarios if u.get("username") or u.get("name_chamados")})
        nomes.sort()
        u_sel = st.selectbox("Usuário", nomes, key="uni_pwd_sel")
        p1 = st.text_input("Nova senha", type="password", key="uni_pwd_p1")
        p2 = st.text_input("Confirmar", type="password", key="uni_pwd_p2")
        if st.button("Alterar senha", type="primary", key="uni_pwd_btn"):
            if len(p1) < 8:
                st.error("Senha deve ter ao menos 8 caracteres.")
            elif p1 != p2:
                st.error("As senhas não conferem.")
            else:
                res = atualizar_senha_unificada(u_sel, p1)
                partes = []
                if res["gerenc"]:
                    partes.append("Gerenciamento")
                if res["chamados"]:
                    partes.append("Chamados")
                if partes:
                    st.success(f"Senha alterada em: {', '.join(partes)}")
                else:
                    st.warning("Usuário não encontrado em nenhum sistema.")

    st.divider()
    st.subheader("Alterar permissão de admin")
    if usuarios:
        nomes_adm = list({u.get("username") or u.get("name_chamados") for u in usuarios if u.get("username") or u.get("name_chamados")})
        nomes_adm.sort()
        u_adm_sel = st.selectbox("Usuário", nomes_adm, key="uni_adm_sel")
        u_obj = next((u for u in usuarios if (u.get("username") or u.get("name_chamados")) == u_adm_sel), {})
        novo_adm = st.checkbox("É administrador", value=bool(u_obj.get("admin_gerenc")), key="uni_adm_check")
        if st.button("Salvar permissão", key="uni_adm_btn"):
            alternar_admin_unificado(u_adm_sel, novo_adm)
            st.success("Permissão atualizada!")
            st.rerun()

    st.divider()
    st.subheader("Desativar / Reativar usuário")
    st.caption("Desativa o acesso do usuário em ambos os sistemas sem excluir o cadastro.")
    if usuarios:
        nomes_desat = list({u.get("username") or u.get("name_chamados") for u in usuarios if u.get("username") or u.get("name_chamados")})
        nomes_desat.sort()
        u_desat_sel = st.selectbox("Usuário", nomes_desat, key="uni_desat_sel")
        u_desat_obj = next((u for u in usuarios if (u.get("username") or u.get("name_chamados")) == u_desat_sel), {})
        esta_ativo = u_desat_obj.get("ativo_gerenc") is not False
        _d1, _d2, _d3 = st.columns([1, 1, 4])
        with _d1:
            if esta_ativo:
                if st.button("🔒 Desativar", key="uni_desat_btn", use_container_width=True):
                    res = desativar_usuario_unificado(u_desat_sel, ativar=False)
                    partes = ([" Gerenciamento"] if res["gerenc"] else []) + ([" Chamados"] if res["chamados"] else [])
                    st.warning(f"Usuário '{u_desat_sel}' desativado em:{', '.join(partes) or ' nenhum sistema'}.")
                    st.rerun()
            else:
                if st.button("🔓 Reativar", key="uni_reativ_btn", use_container_width=True):
                    res = desativar_usuario_unificado(u_desat_sel, ativar=True)
                    partes = ([" Gerenciamento"] if res["gerenc"] else []) + ([" Chamados"] if res["chamados"] else [])
                    st.success(f"Usuário '{u_desat_sel}' reativado em:{', '.join(partes) or ' nenhum sistema'}.")
                    st.rerun()

    st.divider()
    st.subheader("Excluir usuário permanentemente")
    st.caption("Remove o usuário dos dois sistemas. Esta ação não pode ser desfeita.")
    if usuarios:
        nomes_excl = list({u.get("username") or u.get("name_chamados") for u in usuarios if u.get("username") or u.get("name_chamados")})
        nomes_excl.sort()
        u_excl_sel = st.selectbox("Usuário", nomes_excl, key="uni_excl_sel")
        u_excl_obj = next((u for u in usuarios if (u.get("username") or u.get("name_chamados")) == u_excl_sel), {})
        sistemas = []
        if u_excl_obj.get("id_gerenc"):
            sistemas.append("Gerenciamento")
        if u_excl_obj.get("id_chamados"):
            sistemas.append("Chamados")

        confirmar_key = f"uni_excl_confirmar_{u_excl_sel}"
        if st.session_state.get(confirmar_key):
            st.error(
                f"Tem certeza? '{u_excl_sel}' será removido de: **{', '.join(sistemas)}**. "
                "Esta ação é irreversível."
            )
            _ex1, _ex2, _ex3 = st.columns([1, 1, 4])
            with _ex1:
                if st.button("✅ Confirmar exclusão", key="uni_excl_confirmar_btn", use_container_width=True):
                    res = excluir_usuario_unificado(u_excl_sel)
                    partes = ([" Gerenciamento"] if res["gerenc"] else []) + ([" Chamados"] if res["chamados"] else [])
                    st.session_state[confirmar_key] = False
                    st.success(f"Usuário '{u_excl_sel}' excluído de:{', '.join(partes) or ' nenhum sistema'}.")
                    st.rerun()
            with _ex2:
                if st.button("❌ Cancelar", key="uni_excl_cancelar_btn", use_container_width=True):
                    st.session_state[confirmar_key] = False
                    st.rerun()
        else:
            if st.button("🗑️ Excluir usuário", key="uni_excl_btn"):
                st.session_state[confirmar_key] = True
                st.rerun()


# ── Auditoria ─────────────────────────────────────────────────────────────────

def _render_auditoria() -> None:
    try:
        from src.db.repository import listar_auditoria
    except ImportError:
        st.error("Módulo de banco indisponível.")
        return

    st.subheader("Registro de auditoria (últimas 200 ações)")
    registros = listar_auditoria(limit=200)
    if not registros:
        st.caption("Nenhum registro encontrado.")
        return
    df = pd.DataFrame(registros)
    cols = [c for c in ["criado_em", "usuario", "acao", "entidade", "chave", "detalhes"] if c in df.columns]
    if cols:
        df = df[cols].copy()
        df.columns = ["Data/Hora", "Usuário", "Ação", "Entidade", "Chave", "Detalhes"][:len(cols)]
    st.dataframe(df, hide_index=True, use_container_width=True)
