from fastapi import APIRouter
from app.api.v1.endpoints import auth, users, desligamento, tickets, telefones

api_router = APIRouter()

api_router.include_router(auth.router, prefix="/auth", tags=["autenticação"])
api_router.include_router(users.router, prefix="/users", tags=["usuários"])
api_router.include_router(tickets.router, prefix="/tickets", tags=["chamados"])
api_router.include_router(desligamento.router, prefix="/desligamento", tags=["desligamento / gerenciamento de ativos"])
api_router.include_router(telefones.router, prefix="/telefones", tags=["linhas telefônicas"])

