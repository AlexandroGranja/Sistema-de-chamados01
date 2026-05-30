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
    else:
        print("Erro ao criar usuario.")
        sys.exit(1)

if __name__ == "__main__":
    main()
