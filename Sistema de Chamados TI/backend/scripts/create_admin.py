"""
Script para criar usuário administrador inicial
Execute: python scripts/create_admin.py
"""
import sys
import os

# Adicionar diretório raiz ao path
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from sqlalchemy.orm import Session
from app.core.database import SessionLocal, engine
from app.core.security import get_password_hash
from app.models.user import User, UserRole
from app.core.database import Base

def create_admin():
    """Cria usuário administrador inicial"""
    # Criar tabelas se não existirem
    Base.metadata.create_all(bind=engine)
    
    db: Session = SessionLocal()
    
    try:
        # Verificar se já existe admin
        admin = db.query(User).filter(User.email == "admin@promio.com.br").first()
        if admin:
            print("Usuario admin ja existe!")
            return
        
        # Criar admin
        admin = User(
            name="Administrador",
            email="admin@promio.com.br",
            password_hash=get_password_hash("admin123"),  # ALTERAR EM PRODUÇÃO!
            role=UserRole.ADMIN,
            is_active=True
        )
        
        db.add(admin)
        db.commit()
        db.refresh(admin)
        
        print("Usuario administrador criado com sucesso!")
        print("   Email: admin@promio.com.br")
        print("   Senha: admin123")
        print("   ALTERE A SENHA APOS O PRIMEIRO LOGIN!")
        
    except Exception as e:
        db.rollback()
        print("Erro ao criar admin:", e)
    finally:
        db.close()

if __name__ == "__main__":
    create_admin()

