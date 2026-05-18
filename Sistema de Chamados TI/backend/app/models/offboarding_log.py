"""
Registro de baixa de ativos no desligamento de usuário (check-in no Snipe-IT).
"""
from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey, Text
from sqlalchemy.sql import func
from app.core.database import Base


class OffboardingLog(Base):
    __tablename__ = "offboarding_logs"

    id = Column(Integer, primary_key=True, index=True)
    # Usuário do sistema de chamados que está sendo desligado (opcional, para relatório)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    # Dados do ativo no Snipe-IT (para auditoria mesmo se o ativo for alterado lá)
    snipe_asset_id = Column(Integer, nullable=False)
    asset_tag = Column(String(100), nullable=True)
    asset_name = Column(String(255), nullable=True)
    # Condição informada: False = perfeitas condições, True = precisa manutenção
    needs_maintenance = Column(Boolean, nullable=False)
    note = Column(Text, nullable=True)
    # Quem realizou a baixa (usuário do sistema de chamados)
    created_by_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
