from sqlalchemy import Column, Integer, String, Boolean, DateTime, TypeDecorator
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import enum
from app.core.database import Base

class UserRole(str, enum.Enum):
    ADMIN = "admin"
    TECHNICIAN = "technician"
    USER = "user"
    SUPERVISOR = "supervisor"
    # Abre chamados apenas pela URL do portal (cadastro próprio); sem acesso ao painel TI
    REQUESTER = "requester"


class UserRoleColumn(TypeDecorator):
    """
    Mapeia a coluna `role` (PostgreSQL ENUM userrole) para UserRole.

    Alguns bancos retornam labels em MAIÚSCULAS ('ADMIN'); o Enum nativo do SQLAlchemy
    só reconhece os valores em minúsculas ('admin') e dispara LookupError ao ler.
    """

    impl = String(32)
    cache_ok = True

    def process_bind_param(self, value, dialect):
        if value is None:
            return None
        if isinstance(value, UserRole):
            return value.value
        return str(value).strip().lower()

    def process_result_value(self, value, dialect):
        if value is None:
            return None
        if isinstance(value, UserRole):
            return value
        s = str(value).strip().lower()
        try:
            return UserRole(s)
        except ValueError:
            try:
                return UserRole[str(value).strip().upper()]
            except KeyError:
                return UserRole.USER


class User(Base):
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    email = Column(String(255), unique=True, index=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    phone = Column(String(20), nullable=True)
    department = Column(String(100), nullable=True)
    position = Column(String(100), nullable=True)
    role = Column(
        UserRoleColumn(),
        default=UserRole.USER,
        nullable=False,
    )
    avatar_url = Column(String(500), nullable=True)
    is_active = Column(Boolean, default=True, nullable=False)
    snipe_user_id = Column(Integer, nullable=True)  # ID do usuário no Gerenciamento de Ativos (Snipe-IT)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    last_login = Column(DateTime(timezone=True), nullable=True)
    
    # Relationships
    tickets_created = relationship("Ticket", foreign_keys="Ticket.requester_id", back_populates="requester")
    tickets_assigned = relationship("Ticket", foreign_keys="Ticket.assigned_technician_id", back_populates="assigned_technician")
    comments = relationship("Comment", back_populates="user")
    notifications = relationship("Notification", back_populates="user")

