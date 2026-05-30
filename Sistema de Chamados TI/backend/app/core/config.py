import os
import sys
from pathlib import Path
from pydantic_settings import BaseSettings
from typing import List
from dotenv import load_dotenv

# No Windows, .env salvo em "ANSI" (CP1252) pode ter ç, ã etc. Carregar com cp1252 evita UnicodeDecodeError no psycopg2.
_env_encoding = "cp1252" if sys.platform == "win32" else "utf-8"
# Sempre carregar .env da pasta backend (onde fica este arquivo), mesmo rodando de outro diretório
_env_path = Path(__file__).resolve().parent.parent.parent / ".env"
load_dotenv(_env_path, encoding=_env_encoding)


class Settings(BaseSettings):
    # Database (PostgreSQL recomendado; veja env.example e doc/POSTGRES.md)
    DATABASE_URL: str = "postgresql://chamados:chamados@localhost:5432/chamados_ti"

    # JWT
    SECRET_KEY: str = "change-this-secret-key-in-production"
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRATION: int = 3600
    JWT_REFRESH_EXPIRATION: int = 86400

    # Email
    SMTP_HOST: str = "email-ssl.com.br"
    SMTP_PORT: int = 587
    SMTP_USER: str = ""
    SMTP_PASSWORD: str = ""
    SMTP_FROM: str = "noreply@promio.com.br"
    SMTP_USE_TLS: bool = True

    # Cadastro público (/cadastro): telefone é informado sem DDD; concatena-se este DDD (ex.: 11).
    PORTAL_DEFAULT_DDD: str = "11"

    # Application
    API_URL: str = "http://localhost:8000"
    FRONTEND_URL: str = "http://localhost:3000"
    STREAMLIT_APP_URL: str = "http://localhost:8501"
    DEBUG: bool = True
    ENVIRONMENT: str = "development"

    # CORS (no .env use vírgula: http://localhost:3000,http://localhost:5173)
    ALLOWED_ORIGINS: str = "http://localhost:3000,http://localhost:5173"

    # Integração Gerenciamento de Ativos (Snipe-IT)
    SNIPE_BASE_URL: str = "http://192.168.200.131:8082"
    SNIPE_API_TOKEN: str = ""
    SNIPE_STATUS_READY_ID: int = 1
    SNIPE_STATUS_MAINTENANCE_ID: int = 2

    # Integracao com Gerenciamento de Telefones (SQLite externo)
    TELEFONES_SYNC_ENABLED: bool = False
    TELEFONES_DB_PATH: str = ""

    @property
    def allowed_origins_list(self) -> List[str]:
        return [x.strip() for x in self.ALLOWED_ORIGINS.split(",") if x.strip()]

    model_config = {
        "env_file": str(_env_path),
        "env_file_encoding": _env_encoding,
        "extra": "ignore",
        "case_sensitive": True,
    }

settings = Settings()

