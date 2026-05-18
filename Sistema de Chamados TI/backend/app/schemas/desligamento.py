from pydantic import BaseModel
from typing import Optional
from datetime import datetime


class CheckoutRequest(BaseModel):
    """Requisição para entregar ativo a um usuário (check-out no Snipe-IT)."""
    asset_id: int
    snipe_user_id: int
    note: Optional[str] = None
    user_id: Optional[int] = None  # ID do usuário no sistema de chamados (para relatório)


class CheckoutByTagRequest(BaseModel):
    """Requisição para entregar ativo por patrimônio para colaborador (cria colaborador se necessário)."""
    collaborator_name: str
    asset_tag: str
    note: Optional[str] = None
    user_id: Optional[int] = None


class CheckinRequest(BaseModel):
    """Requisição para dar baixa em um ativo no Gerenciamento de Ativos."""
    asset_id: int  # ID do ativo no Snipe-IT
    needs_maintenance: bool  # True = precisa manutenção, False = perfeitas condições
    note: Optional[str] = None
    user_id: Optional[int] = None  # ID do usuário no sistema de chamados (para log/relatório)
    snipe_user_id: Optional[int] = None  # ID do usuário no Gerenciamento (para exclusão após última baixa)
    delete_user_when_no_assets: bool = False  # Excluir usuário automaticamente quando não restarem ativos


class OffboardingLogSchema(BaseModel):
    id: int
    user_id: Optional[int] = None
    snipe_asset_id: int
    asset_tag: Optional[str] = None
    asset_name: Optional[str] = None
    needs_maintenance: bool
    note: Optional[str] = None
    created_by_id: int
    created_at: datetime

    class Config:
        from_attributes = True


class AssetAssignmentSchema(BaseModel):
    id: int
    user_id: Optional[int] = None
    snipe_user_id: int
    snipe_user_name: Optional[str] = None
    snipe_asset_id: int
    asset_tag: Optional[str] = None
    asset_name: Optional[str] = None
    note: Optional[str] = None
    assigned_by_id: int
    assigned_at: datetime

    class Config:
        from_attributes = True
