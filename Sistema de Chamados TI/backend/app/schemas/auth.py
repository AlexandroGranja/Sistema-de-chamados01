from pydantic import BaseModel, EmailStr, Field
from typing import Optional

class Token(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"

class TokenData(BaseModel):
    user_id: Optional[int] = None
    email: Optional[str] = None

class LoginRequest(BaseModel):
    """Campo `email` aceita e-mail **ou** nome de usuário (mesmo login do Gerenciamento de Telefones)."""
    email: str = Field(..., min_length=1, description="E-mail ou usuário")
    password: str = Field(..., min_length=1)


class PortalRegisterRequest(BaseModel):
    """Cadastro público: abrir chamados com a TI (acesso restrito ao formulário)."""
    first_name: str = Field(..., min_length=1, max_length=120, description="Nome")
    last_name: str = Field(..., min_length=1, max_length=120, description="Sobrenome")
    email: EmailStr = Field(..., description="E-mail para login")
    password: str = Field(..., min_length=6, max_length=128)
    password_confirm: str = Field(..., min_length=6, max_length=128)
    department: str = Field(..., min_length=1, max_length=100, description="Setor")

class RefreshTokenRequest(BaseModel):
    refresh_token: str

class SSOExchangeRequest(BaseModel):
    sso_code: str


class OIDCExchangeRequest(BaseModel):
    oidc_code: str

class ForgotPasswordRequest(BaseModel):
    email: EmailStr

class ResetPasswordRequest(BaseModel):
    token: str
    new_password: str

