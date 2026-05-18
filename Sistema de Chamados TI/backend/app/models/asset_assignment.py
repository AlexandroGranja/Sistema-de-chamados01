"""
Registro de entrega de ativo (check-out no Snipe-IT): quem recebeu qual aparelho e quando.
"""
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Text
from sqlalchemy.sql import func
from app.core.database import Base


class AssetAssignment(Base):
    __tablename__ = "asset_assignments"

    id = Column(Integer, primary_key=True, index=True)
    # Usuário do sistema de chamados (opcional - para relatório)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    # ID do usuário no Snipe-IT que recebeu o ativo
    snipe_user_id = Column(Integer, nullable=False)
    snipe_user_name = Column(String(255), nullable=True)
    # Ativo no Snipe-IT
    snipe_asset_id = Column(Integer, nullable=False)
    asset_tag = Column(String(100), nullable=True)
    asset_name = Column(String(255), nullable=True)
    note = Column(Text, nullable=True)
    # Quem fez a entrega (usuário do sistema de chamados)
    assigned_by_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    assigned_at = Column(DateTime(timezone=True), server_default=func.now())
