from datetime import date, datetime
from enum import Enum
from typing import List, Optional

from pydantic import BaseModel

from app.models.ticket import (
    TicketImpact,
    TicketPriority,
    TicketStatus,
    TicketType,
    TicketUrgency,
)


class OffboardingAction(str, Enum):
    DEVICE_OK = "device_ok"
    OFFBOARDING_WITH_MAINTENANCE = "offboarding_with_maintenance"
    MAINTENANCE_ONLY = "maintenance_only"
    WITHOUT_CHARGER = "without_charger"
    NOT_DELIVERED = "not_delivered"


class DeviceCondition(str, Enum):
    OK = "ok"
    MAINTENANCE = "maintenance"


class TicketBase(BaseModel):
    title: str
    description: str
    ticket_type: TicketType = TicketType.REQUEST
    category: Optional[str] = None
    subcategory: Optional[str] = None
    priority: TicketPriority = TicketPriority.MEDIUM
    urgency: Optional[TicketUrgency] = TicketUrgency.MEDIUM
    impact: Optional[TicketImpact] = TicketImpact.MEDIUM
    status: TicketStatus = TicketStatus.OPEN
    location: Optional[str] = None
    equipment_info: Optional[str] = None
    internal_notes: Optional[str] = None
    assigned_technician_id: Optional[int] = None


class TicketCreate(TicketBase):
    requester_id: Optional[int] = None


class TicketStatusUpdate(BaseModel):
    status: TicketStatus
    internal_notes: Optional[str] = None


class TicketUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    status: Optional[TicketStatus] = None
    category: Optional[str] = None
    subcategory: Optional[str] = None
    location: Optional[str] = None
    internal_notes: Optional[str] = None
    user_department: Optional[str] = None
    device_model: Optional[str] = None
    asset_tag: Optional[str] = None
    reason: Optional[str] = None


class TicketOffboardingCreate(BaseModel):
    action: OffboardingAction
    employee_name: str
    return_date: Optional[date] = None
    asset_tag: Optional[str] = None
    device_model: Optional[str] = None
    user_department: Optional[str] = None
    device_condition: DeviceCondition = DeviceCondition.OK
    maintenance_reason: Optional[str] = None
    resolution_text: Optional[str] = None


class TicketOut(BaseModel):
    id: int
    ticket_number: str
    title: str
    description: str
    ticket_type: TicketType
    category: Optional[str] = None
    subcategory: Optional[str] = None
    priority: TicketPriority
    urgency: Optional[TicketUrgency] = None
    impact: Optional[TicketImpact] = None
    status: TicketStatus
    requester_id: int
    assigned_technician_id: Optional[int] = None
    location: Optional[str] = None
    equipment_info: Optional[str] = None
    internal_notes: Optional[str] = None
    created_at: datetime
    updated_at: Optional[datetime] = None
    resolved_at: Optional[datetime] = None
    closed_at: Optional[datetime] = None
    # Preenchido na listagem (PostgreSQL): nome/perfil vindo de `users` por id ou snipe_user_id = solicitante
    requester_name: Optional[str] = None
    requester_role: Optional[str] = None

    class Config:
        from_attributes = True


class StaffRequesterAlertItem(BaseModel):
    """Chamado novo aberto por usuário do portal (perfil requester)."""

    id: int
    ticket_number: str
    title: str
    created_at: datetime
    requester_name: Optional[str] = None


class StaffRequesterAlertsOut(BaseModel):
    items: List[StaffRequesterAlertItem]
    server_time: datetime
