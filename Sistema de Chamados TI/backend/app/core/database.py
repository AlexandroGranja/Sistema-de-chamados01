from urllib.parse import quote_plus, unquote, urlparse, urlunparse
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from app.core.config import settings


def _normalize_database_url(url: str) -> str:
    """Garante que a URL do banco use apenas ASCII na conexão (evita UnicodeDecodeError no psycopg2 no Windows)."""
    url = url.strip()
    if url.startswith("sqlite://"):
        return url
    try:
        parsed = urlparse(url)
        # Codifica user e password para ASCII (percent-encoding), evitando ç, ã etc. no DSN
        netloc = parsed.hostname or "localhost"
        if parsed.port:
            netloc = f"{netloc}:{parsed.port}"
        if parsed.username or parsed.password:
            # urlparse NÃO decodifica %XX na senha; sem unquote, %24 vira literal e vira %2524 após quote_plus.
            user = quote_plus(unquote(parsed.username or "")) if parsed.username else ""
            password = quote_plus(unquote(parsed.password or "")) if parsed.password else ""
            netloc = f"{user}:{password}@{netloc}" if (user or password) else netloc
        path = parsed.path or "/chamados_ti"
        new = urlunparse((parsed.scheme, netloc, path, parsed.params, parsed.query, parsed.fragment))
        # Garantir só ASCII no DSN (evita UnicodeDecodeError no psycopg2 no Windows)
        return new.encode("ascii", errors="replace").decode("ascii")
    except Exception:
        return url


_db_url = _normalize_database_url(settings.DATABASE_URL)
_connect_args = {}
if _db_url.startswith("sqlite"):
    _connect_args["check_same_thread"] = False
engine = create_engine(
    _db_url,
    pool_pre_ping=not _db_url.startswith("sqlite"),
    pool_size=10,
    max_overflow=20,
    connect_args=_connect_args,
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

def get_db():
    """Dependency para obter sessão do banco de dados"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

