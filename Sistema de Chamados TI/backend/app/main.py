import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from fastapi.exception_handlers import http_exception_handler, request_validation_exception_handler
from sqlalchemy.exc import OperationalError
from starlette.middleware.base import BaseHTTPMiddleware
from app.core.config import settings
from app.api.v1.api import api_router

logger = logging.getLogger(__name__)


def _ensure_postgres_userrole_requester() -> None:
    """Garante valor 'requester' no ENUM PostgreSQL (caso migração Alembic não tenha sido aplicada)."""
    try:
        from sqlalchemy import text
        from app.core.database import engine
        url = str(engine.url)
        if not (url.startswith("postgresql") or "postgres" in url.lower()):
            return
        with engine.connect() as conn:
            conn.execute(
                text(
                    """
                    DO $$ BEGIN
                        ALTER TYPE userrole ADD VALUE 'requester';
                    EXCEPTION
                        WHEN duplicate_object THEN NULL;
                    END $$;
                    """
                )
            )
            conn.commit()
    except Exception as e:
        logger.warning("Não foi possível garantir ENUM userrole.requester: %s", e)


@asynccontextmanager
async def lifespan(app: FastAPI):
    from app.core import snipe_status as snipe_state
    # Garante criação das tabelas locais (incluindo chamados) em ambiente de desenvolvimento.
    try:
        from app.core.database import Base, engine
        import app.models  # noqa: F401
        Base.metadata.create_all(bind=engine)
        _ensure_postgres_userrole_requester()
    except Exception as e:
        logger.warning("Falha ao garantir tabelas no startup: %s", e)

    try:
        from app.services.snipe import is_configured
        ok = is_configured()
        snipe_state.snipe_configured_at_startup = ok
        logger.info("Snipe-IT integrado: %s", ok)
        print(f"[Snipe-IT] Integração configurada: {ok}")
    except Exception as e:
        snipe_state.snipe_configured_at_startup = False
        logger.warning("Snipe-IT status na subida: %s", e)
        print(f"[Snipe-IT] Erro ao verificar: {e}")
    yield


app = FastAPI(
    title="Sistema de Chamados TI",
    description="API para gestão de chamados do setor de TI",
    version="1.0.0",
    docs_url="/api/docs",
    redoc_url="/api/redoc",
    lifespan=lifespan,
)

class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Permissions-Policy"] = "geolocation=(), microphone=(), camera=()"
        return response


# Ordem de registro: CORS (último adicionado = mais externo) → SecurityHeaders
app.add_middleware(SecurityHeadersMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["*"],
)


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """Evita que 422 vire 500 por causa do handler genérico de Exception."""
    return await request_validation_exception_handler(request, exc)


@app.exception_handler(OperationalError)
async def sqlalchemy_operational_handler(request: Request, exc: OperationalError):
    """Conexão com PostgreSQL recusada, timeout, etc."""
    logger.exception("Erro operacional do banco (conexão): %s", exc)
    return JSONResponse(
        status_code=503,
        content={
            "detail": "Não foi possível conectar ao banco de dados. Verifique DATABASE_URL, rede e se o PostgreSQL está em execução.",
            "error": str(exc) if settings.DEBUG else None,
        },
        headers={
            "Access-Control-Allow-Origin": request.headers.get("origin") or "*",
            "Access-Control-Allow-Credentials": "true",
        },
    )


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Garante que erros 500 tenham CORS e log do erro real.
    Não engole HTTPException (senão 400/503 virariam 500 genérico)."""
    if isinstance(exc, HTTPException):
        return await http_exception_handler(request, exc)
    # Handlers mais específicos (OperationalError, RequestValidationError) já tratados acima
    logger.exception("Erro não tratado: %s", exc)
    return JSONResponse(
        status_code=500,
        content={
            "detail": "Erro interno do servidor. Verifique os logs do backend e a conexão com o banco (DATABASE_URL).",
            "error": str(exc) if settings.DEBUG else None,
        },
        headers={
            "Access-Control-Allow-Origin": request.headers.get("origin") or "*",
            "Access-Control-Allow-Credentials": "true",
        },
    )

# Incluir rotas da API
app.include_router(api_router, prefix="/api")


@app.get("/")
async def root():
    return {"message": "Sistema de Chamados TI API", "version": "1.0.0"}

@app.get("/health")
async def health_check():
    return {"status": "healthy"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.DEBUG
    )

