#!/usr/bin/env python
"""
Cria o primeiro usuário administrador.
Execute uma vez para configurar o login inicial.

Uso: python -m scripts.criar_admin
"""

import getpass
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from src.db.repository import init_db, criar_usuario, tem_usuarios
from src.core.config import is_postgres_configured

def main():
    init_db()
    if tem_usuarios():
        print("Ja existem usuarios. Use o app para criar novos (como admin).")
        return
    print("Criando primeiro usuario administrador...")
    print("Dica: ao pedir a senha no PowerShell, as letras NAO aparecem — isso e normal.")
    username = input("Usuario: ").strip()
    if not username:
        print("Usuario invalido.")
        sys.exit(1)
    if sys.platform == "win32":
        print("(Use input visivel no Windows para evitar confusao.)")
        password = input("Senha (min. 4 caracteres): ")
        confirm = input("Confirme a senha: ")
    else:
        password = getpass.getpass("Senha: ")
        confirm = getpass.getpass("Confirme a senha: ")
    if password != confirm:
        print("As senhas nao coincidem.")
        sys.exit(1)
    if len(password) < 4:
        print("Senha deve ter pelo menos 4 caracteres.")
        sys.exit(1)
    if criar_usuario(username, password, is_admin=True):
        print(f"Usuario '{username}' criado com sucesso!")
        if is_postgres_configured():
            try:
                from scripts.sync_usuarios_chamados import executar_sync

                ok, msg = executar_sync()
                if ok:
                    print(f"Sync Chamados: {msg}")
                else:
                    print(f"Aviso — sync Chamados falhou: {msg}")
                    print("Rode depois: python -m scripts.sync_usuarios_chamados")
            except Exception as exc:
                print(f"Aviso — sync Chamados: {exc}")
                print("Rode depois: python -m scripts.sync_usuarios_chamados")
    else:
        print("Erro ao criar usuario.")
        sys.exit(1)

if __name__ == "__main__":
    main()
