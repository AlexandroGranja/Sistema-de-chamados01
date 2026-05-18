from pydantic import BaseModel, Field, model_validator
from typing import Optional
from datetime import datetime
from app.models.user import UserRole


class UserBase(BaseModel):
    name: str
    email: str
    phone: Optional[str] = None
    department: Optional[str] = None
    position: Optional[str] = None
    role: UserRole = UserRole.USER


class UserCreate(BaseModel):
    """Criação por admin: equipe (e-mail) ou usuário padrão / portal (nome, sobrenome, telefone)."""

    password: str = Field(..., min_length=6)
    password_confirm: Optional[str] = None
    role: UserRole = UserRole.USER
    department: Optional[str] = None
    position: Optional[str] = None
    # Equipe (admin / técnico)
    name: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    # Usuário padrão (só abre chamado)
    first_name: Optional[str] = None
    last_name: Optional[str] = None

    @model_validator(mode="after")
    def validate_create(self):
        if self.password_confirm is not None and self.password != self.password_confirm:
            raise ValueError("As senhas não conferem.")
        if self.role == UserRole.REQUESTER:
            fn = (self.first_name or "").strip()
            ln = (self.last_name or "").strip()
            if not fn or not ln:
                raise ValueError("Nome e sobrenome são obrigatórios.")
            if not (self.phone or "").strip():
                raise ValueError("Telefone é obrigatório.")
        else:
            if not (self.name or "").strip():
                raise ValueError("Nome é obrigatório.")
            if not (self.email or "").strip():
                raise ValueError("E-mail é obrigatório.")
        return self


class UserUpdate(BaseModel):
    name: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    department: Optional[str] = None
    position: Optional[str] = None
    role: Optional[UserRole] = None
    is_active: Optional[bool] = None
    snipe_user_id: Optional[int] = None


class UserPasswordUpdate(BaseModel):
    current_password: str
    new_password: str


class UserInDB(UserBase):
    id: int
    avatar_url: Optional[str] = None
    is_active: bool
    snipe_user_id: Optional[int] = None
    created_at: datetime
    updated_at: Optional[datetime] = None
    last_login: Optional[datetime] = None

    class Config:
        from_attributes = True


class User(UserInDB):
    pass
