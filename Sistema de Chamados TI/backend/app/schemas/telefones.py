from typing import Optional
from pydantic import BaseModel


class LinhaPreview(BaseModel):
    """Dados da linha para prévia antes de confirmar qualquer ação."""
    id: int
    nome: Optional[str] = None
    linha: Optional[str] = None
    equipe: Optional[str] = None
    aparelho: Optional[str] = None
    modelo: Optional[str] = None
    imei_a: Optional[str] = None
    imei_b: Optional[str] = None
    marca: Optional[str] = None
    chip: Optional[str] = None
    operadora: Optional[str] = None
    numero_serie: Optional[str] = None
    ativo: Optional[str] = None  # número do ativo (ex: "001415")
    cargo: Optional[str] = None
    setor: Optional[str] = None
    gestor: Optional[str] = None
    email: Optional[str] = None
    codigo: Optional[str] = None


class BuscarLinhaResponse(BaseModel):
    encontrado: bool
    mensagem: str
    linha: Optional[LinhaPreview] = None


class OnboardingRequest(BaseModel):
    """Dados para atribuir linha a novo colaborador."""
    numero_linha: str
    nome: str
    codigo: Optional[str] = None
    cargo: Optional[str] = None
    setor: Optional[str] = None
    empresa: Optional[str] = None
    equipe: Optional[str] = None
    gestor: Optional[str] = None
    email: Optional[str] = None
    nome_guerra: Optional[str] = None
    substituicao_nome: Optional[str] = None
    ticket_id: Optional[int] = None


class ManutencaoRequest(BaseModel):
    """Dados para atualizar aparelho durante manutenção (troca por reserva)."""
    linha_id: int
    imei_a: Optional[str] = None
    imei_b: Optional[str] = None
    marca: Optional[str] = None
    modelo: Optional[str] = None
    aparelho: Optional[str] = None
    numero_serie: Optional[str] = None
    ativo: Optional[str] = None  # número do ativo (ex: "001415")
    chip: Optional[str] = None
    observacao: Optional[str] = None
    ticket_id: Optional[int] = None


class RouboPerdaRequest(BaseModel):
    """
    Roubo/Perda — dois cenários:
    - cenario_a: mesma linha, aparelho novo (nova_linha = None)
    - cenario_b: linha nova + aparelho novo (nova_linha preenchida)
    """
    linha_id: int
    imei_a: Optional[str] = None
    imei_b: Optional[str] = None
    marca: Optional[str] = None
    modelo: Optional[str] = None
    aparelho: Optional[str] = None
    numero_serie: Optional[str] = None
    ativo: Optional[str] = None  # número do ativo (ex: "001415")
    chip: Optional[str] = None
    nova_linha: Optional[str] = None
    observacao: Optional[str] = None
    ticket_id: Optional[int] = None


class TransferenciaRequest(BaseModel):
    """Transferência entre equipes (com ou sem promoção)."""
    linha_id: int
    equipe: str
    setor: str
    gestor: str
    cargo: Optional[str] = None
    empresa: Optional[str] = None
    observacao: Optional[str] = None
    ticket_id: Optional[int] = None


class EquipesSetoresResponse(BaseModel):
    equipes: list[str] = []
    setores: list[str] = []
    gestores: list[str] = []
    empresas: list[str] = []


class BuscarLinhaPorNumeroResponse(BaseModel):
    encontrado: bool
    mensagem: str
    linha: Optional[LinhaPreview] = None


class NovaLinhaRequest(BaseModel):
    """Cria uma linha nova do zero — para novos setores/equipes."""
    numero_linha: str
    nome: str
    codigo: Optional[str] = None
    equipe: Optional[str] = None
    setor: Optional[str] = None
    gestor: Optional[str] = None
    empresa: Optional[str] = None
    cargo: Optional[str] = None
    email: Optional[str] = None
    nome_guerra: Optional[str] = None
    imei_a: Optional[str] = None
    imei_b: Optional[str] = None
    marca: Optional[str] = None
    modelo: Optional[str] = None
    aparelho: Optional[str] = None
    numero_serie: Optional[str] = None
    ativo: Optional[str] = None
    chip: Optional[str] = None
    operadora: Optional[str] = None
    ticket_id: Optional[int] = None


class TelefonesActionResponse(BaseModel):
    sucesso: bool
    mensagem: str


class StreamlitLinkResponse(BaseModel):
    url: str


class ListarLinhasResponse(BaseModel):
    modo: str
    total: int
    rows: list[dict]
