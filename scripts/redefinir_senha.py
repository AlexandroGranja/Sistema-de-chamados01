#!/usr/bin/env python
"""
Redefine a senha de um usuário existente (usuarios_app).

Uso:
  python -m scripts.redefinir_senha
  python -m scripts.redefinir_senha "alexandro granja"
"""

from __future__ import annotations

import getpass
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from src.db.repository import atualizar_senha_usuario, listar_usuarios


def _ler_senha(mensagem: str) -> str:
    """Lê senha; no Windows usa input visível (getpass costuma confundir no PowerShell)."""
    if sys.platform == "win32":
        print("(A senha aparece na tela — use este terminal só você.)")
        return input(mensagem)
    try:
        return getpass.getpass(mensagem)
    except (EOFError, KeyboardInterrupt):
        return ""


def main() -> int:
    usuarios = listar_usuarios()
    if not usuarios:
        print("Nenhum usuario cadastrado.")
        return 1

    print("Usuarios cadastrados:")
    for u in usuarios:
        admin = "admin" if u.get("is_admin") else "operador"
        print(f"  - {u['username']} ({admin})")

    username = " ".join(sys.argv[1:]).strip() if len(sys.argv) > 1 else input("\nUsuario para redefinir senha: ").strip()
    if not username:
        print("Usuario invalido.")
        return 1

    nomes = {u["username"] for u in usuarios}
    alvo = username.strip().lower()
    if alvo not in nomes:
        print(f"Usuario '{username}' nao encontrado.")
        return 1

    senha = _ler_senha("Nova senha (min. 4 caracteres): ")
    if len(senha) < 4:
        print("Senha deve ter pelo menos 4 caracteres.")
        return 1

    confirmacao = _ler_senha("Confirme a nova senha: ")
    if senha != confirmacao:
        print("As senhas nao coincidem.")
        return 1

    if atualizar_senha_usuario(alvo, senha):
        print(f"Senha de '{alvo}' atualizada com sucesso.")
        print("Use o mesmo usuario/senha no Gerenciamento (8501) e no Chamados (3000).")
        return 0

    print("Nao foi possivel atualizar a senha.")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
