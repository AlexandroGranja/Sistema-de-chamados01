"""
Endpoints de integração com a tabela `linhas` do Gerenciamento de Telefones.
Todos exigem autenticação de técnico ou admin.
"""
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
)
from app.services.telefones import (
    buscar_linha_por_codigo_ou_nome,
    buscar_linha_por_numero,
    listar_equipes_e_setores,
    criar_nova_linha,
    atribuir_linha,
    atualizar_aparelho,
    registrar_roubo_perda,
    transferir_colaborador,
)

router = APIRouter()


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
    ok, msg = transferir_colaborador(
        linha_id=body.linha_id,
        equipe=body.equipe,
        setor=body.setor,
        gestor=body.gestor,
        cargo=body.cargo or "",
        empresa=body.empresa or "",
        observacao_extra=body.observacao or "",
        ticket_id=body.ticket_id,
    )
    if not ok:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=msg)
    return TelefonesActionResponse(sucesso=True, mensagem=msg)
