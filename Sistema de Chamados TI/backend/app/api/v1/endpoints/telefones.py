"""
Endpoints de integração com a tabela `linhas` do Gerenciamento de Telefones.
Todos exigem autenticação de técnico ou admin.
"""
from typing import Optional, Tuple

from fastapi import APIRouter, Depends, HTTPException, status
from app.api.v1.dependencies import get_current_technician_or_admin
from app.models.user import User
from app.schemas.telefones import (
    BuscarLinhaResponse,
    BuscarLinhaPorNumeroResponse,
    EquipesSetoresResponse,
    LinhaPreview,
    OnboardingRequest,
    NovaLinhaRequest,
    ManutencaoRequest,
    RouboPerdaRequest,
    TransferenciaRequest,
    TelefonesActionResponse,
    StreamlitLinkResponse,
    ListarLinhasResponse,
    SalvarLinhasRequest,
    SalvarLinhasResponse,
)
from app.services.streamlit_links import build_streamlit_linha_url
from app.services.telefones import (
    buscar_linha_por_codigo_ou_nome,
    buscar_linha_por_numero,
    listar_equipes_e_setores,
    listar_linhas_grid,
    salvar_linhas_grid,
    criar_nova_linha,
    atribuir_linha,
    atualizar_aparelho,
    registrar_roubo_perda,
    transferir_colaborador,
)

router = APIRouter()


def _audit_actor(user: User) -> Tuple[Optional[int], str]:
    audit_user_id = int(user.snipe_user_id) if user.snipe_user_id is not None else None
    audit_username = (user.email or user.name or "").strip()
    return audit_user_id, audit_username


@router.get("/buscar-linha", response_model=BuscarLinhaResponse)
async def buscar_linha(
    codigo: str = "",
    nome: str = "",
    current_user: User = Depends(get_current_technician_or_admin),
):
    """
    Busca linha por código (matrícula) com fallback por nome.
    Retorna dados para prévia antes de qualquer ação.
    """
    if not codigo.strip() and not nome.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Informe código ou nome para buscar.",
        )
    row = buscar_linha_por_codigo_ou_nome(codigo=codigo, nome=nome)
    if not row:
        return BuscarLinhaResponse(
            encontrado=False,
            mensagem=f"Nenhuma linha ativa encontrada para código='{codigo}' / nome='{nome}'.",
        )
    preview = LinhaPreview(
        id=row["id"],
        nome=row.get("nome") or row.get("nome_usuario_snapshot"),
        linha=row.get("linha"),
        equipe=row.get("equipe") or row.get("equipe_padrao"),
        aparelho=row.get("aparelho"),
        modelo=row.get("modelo"),
        imei_a=row.get("imei_a"),
        imei_b=row.get("imei_b"),
        marca=row.get("marca"),
        chip=row.get("chip"),
        operadora=row.get("operadora"),
        numero_serie=row.get("numero_serie"),
        ativo=row.get("ativo") or row.get("patrimonio"),
        cargo=row.get("cargo"),
        setor=row.get("setor"),
        gestor=row.get("gestor"),
        email=row.get("email"),
        codigo=row.get("codigo") or row.get("codigo_usuario_snapshot"),
    )
    return BuscarLinhaResponse(encontrado=True, mensagem="Linha encontrada.", linha=preview)


@router.get("/opcoes", response_model=EquipesSetoresResponse)
async def opcoes_equipes_setores(
    current_user: User = Depends(get_current_technician_or_admin),
):
    """Retorna listas distintas de equipes, setores, gestores e empresas para autocomplete."""
    return listar_equipes_e_setores()


@router.get("/linhas", response_model=ListarLinhasResponse)
async def listar_linhas(
    modo: str = "ativas",
    current_user: User = Depends(get_current_technician_or_admin),
):
    """Lista linhas para grid do Gerenciamento (chaves legadas Codigo/Nome/Linha…)."""
    modo_norm = (modo or "ativas").strip().lower()
    if modo_norm not in {"ativas", "desativadas"}:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="modo deve ser 'ativas' ou 'desativadas'.",
        )
    rows = listar_linhas_grid(modo=modo_norm)
    return ListarLinhasResponse(modo=modo_norm, total=len(rows), rows=rows)


@router.post("/linhas/salvar-lote", response_model=SalvarLinhasResponse)
async def salvar_linhas_lote(
    body: SalvarLinhasRequest,
    current_user: User = Depends(get_current_technician_or_admin),
):
    """Salva lote de linhas do grid Streamlit (UPSERT por numero_linha)."""
    modo_norm = (body.modo or "ativas").strip().lower()
    if modo_norm not in {"ativas", "desativadas"}:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="modo deve ser 'ativas' ou 'desativadas'.",
        )
    if not body.rows:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Informe ao menos uma linha em rows.",
        )
    try:
        total = salvar_linhas_grid(rows=body.rows, modo=modo_norm)
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Falha ao salvar linhas: {exc}",
        ) from exc
    return SalvarLinhasResponse(
        sucesso=True,
        mensagem=f"{total} linha(s) persistida(s).",
        total=total,
    )


@router.get("/link-gerenciamento", response_model=StreamlitLinkResponse)
async def link_gerenciamento(
    ticket_id: Optional[int] = None,
    linha: str = "",
    segmento: str = "",
    equipe: str = "",
    return_url: str = "",
    current_user: User = Depends(get_current_technician_or_admin),
):
    """Gera URL do Streamlit com contexto de chamado/linha e retorno ao React."""
    url = build_streamlit_linha_url(
        ticket_id=ticket_id,
        linha=linha,
        segmento=segmento,
        equipe=equipe,
        return_url=return_url,
    )
    return StreamlitLinkResponse(url=url)


@router.get("/buscar-linha-numero", response_model=BuscarLinhaPorNumeroResponse)
async def buscar_linha_numero(
    numero: str = "",
    current_user: User = Depends(get_current_technician_or_admin),
):
    """
    Busca linha pelo número de telefone (inclui linhas VAGO).
    Usado no fluxo Novo Usuário para pré-preencher equipe/gestor/setor/empresa.
    """
    if not numero.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Informe o número da linha.",
        )
    row = buscar_linha_por_numero(numero=numero)
    if not row:
        return BuscarLinhaPorNumeroResponse(
            encontrado=False,
            mensagem=f"Nenhuma linha encontrada para o número '{numero}'.",
        )
    preview = LinhaPreview(
        id=row["id"],
        nome=row.get("nome") or row.get("nome_usuario_snapshot"),
        linha=row.get("linha"),
        equipe=row.get("equipe") or row.get("equipe_padrao"),
        aparelho=row.get("aparelho"),
        modelo=row.get("modelo"),
        imei_a=row.get("imei_a"),
        imei_b=row.get("imei_b"),
        marca=row.get("marca"),
        chip=row.get("chip"),
        operadora=row.get("operadora"),
        numero_serie=row.get("numero_serie"),
        ativo=row.get("ativo") or row.get("patrimonio"),
        cargo=row.get("cargo"),
        setor=row.get("setor"),
        gestor=row.get("gestor"),
        email=row.get("email"),
        codigo=row.get("codigo") or row.get("codigo_usuario_snapshot"),
    )
    return BuscarLinhaPorNumeroResponse(encontrado=True, mensagem="Linha encontrada.", linha=preview)


@router.post("/nova-linha", response_model=TelefonesActionResponse)
async def nova_linha(
    body: NovaLinhaRequest,
    current_user: User = Depends(get_current_technician_or_admin),
):
    """Cria uma nova linha do zero — para novos setores, equipes ou colaboradores sem linha cadastrada."""
    audit_user_id, audit_username = _audit_actor(current_user)
    ok, msg = criar_nova_linha(
        numero_linha=body.numero_linha,
        nome=body.nome,
        codigo=body.codigo or "",
        equipe=body.equipe or "",
        setor=body.setor or "",
        gestor=body.gestor or "",
        empresa=body.empresa or "",
        cargo=body.cargo or "",
        email=body.email or "",
        nome_guerra=body.nome_guerra or "",
        imei_a=body.imei_a or "",
        imei_b=body.imei_b or "",
        marca=body.marca or "",
        modelo=body.modelo or "",
        aparelho=body.aparelho or "",
        numero_serie=body.numero_serie or "",
        ativo=body.ativo or "",
        chip=body.chip or "",
        operadora=body.operadora or "",
        ticket_id=body.ticket_id,
        audit_user_id=audit_user_id,
        audit_username=audit_username,
    )
    if not ok:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=msg)
    return TelefonesActionResponse(sucesso=True, mensagem=msg)


@router.post("/onboarding", response_model=TelefonesActionResponse)
async def onboarding_linha(
    body: OnboardingRequest,
    current_user: User = Depends(get_current_technician_or_admin),
):
    """Atribui novo colaborador a uma linha."""
    audit_user_id, audit_username = _audit_actor(current_user)
    ok, msg = atribuir_linha(
        numero_linha=body.numero_linha,
        nome=body.nome,
        codigo=body.codigo or "",
        cargo=body.cargo or "",
        setor=body.setor or "",
        empresa=body.empresa or "",
        equipe=body.equipe or "",
        gestor=body.gestor or "",
        email=body.email or "",
        nome_guerra=body.nome_guerra or "",
        ticket_id=body.ticket_id,
        audit_user_id=audit_user_id,
        audit_username=audit_username,
    )
    if not ok:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=msg)
    return TelefonesActionResponse(sucesso=True, mensagem=msg)


@router.post("/manutencao", response_model=TelefonesActionResponse)
async def manutencao_aparelho(
    body: ManutencaoRequest,
    current_user: User = Depends(get_current_technician_or_admin),
):
    """Atualiza dados do aparelho (troca por reserva). Preserva dados do colaborador."""
    audit_user_id, audit_username = _audit_actor(current_user)
    ok, msg = atualizar_aparelho(
        linha_id=body.linha_id,
        imei_a=body.imei_a or "",
        imei_b=body.imei_b or "",
        marca=body.marca or "",
        modelo=body.modelo or "",
        aparelho=body.aparelho or "",
        numero_serie=body.numero_serie or "",
        ativo=body.ativo or "",
        chip=body.chip or "",
        observacao_extra=body.observacao or "",
        ticket_id=body.ticket_id,
        audit_user_id=audit_user_id,
        audit_username=audit_username,
    )
    if not ok:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=msg)
    return TelefonesActionResponse(sucesso=True, mensagem=msg)


@router.post("/roubo-perda", response_model=TelefonesActionResponse)
async def roubo_perda_linha(
    body: RouboPerdaRequest,
    current_user: User = Depends(get_current_technician_or_admin),
):
    """
    Registra roubo/perda.
    Cenário A: mesmo número, novo aparelho.
    Cenário B: nova linha + novo aparelho (preencher nova_linha).
    """
    audit_user_id, audit_username = _audit_actor(current_user)
    ok, msg = registrar_roubo_perda(
        linha_id=body.linha_id,
        imei_a=body.imei_a or "",
        imei_b=body.imei_b or "",
        marca=body.marca or "",
        modelo=body.modelo or "",
        aparelho=body.aparelho or "",
        numero_serie=body.numero_serie or "",
        ativo=body.ativo or "",
        chip=body.chip or "",
        nova_linha=body.nova_linha or "",
        observacao_extra=body.observacao or "",
        ticket_id=body.ticket_id,
        audit_user_id=audit_user_id,
        audit_username=audit_username,
    )
    if not ok:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=msg)
    return TelefonesActionResponse(sucesso=True, mensagem=msg)


@router.post("/transferencia", response_model=TelefonesActionResponse)
async def transferencia_equipe(
    body: TransferenciaRequest,
    current_user: User = Depends(get_current_technician_or_admin),
):
    """Transfere colaborador de equipe. Atualiza equipe, setor, gestor e opcionalmente cargo/empresa."""
    audit_user_id, audit_username = _audit_actor(current_user)
    ok, msg = transferir_colaborador(
        linha_id=body.linha_id,
        equipe=body.equipe,
        setor=body.setor,
        gestor=body.gestor,
        cargo=body.cargo or "",
        empresa=body.empresa or "",
        observacao_extra=body.observacao or "",
        ticket_id=body.ticket_id,
        audit_user_id=audit_user_id,
        audit_username=audit_username,
    )
    if not ok:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=msg)
    return TelefonesActionResponse(sucesso=True, mensagem=msg)
