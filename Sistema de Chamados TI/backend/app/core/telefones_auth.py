"""
Compatibilidade de senha com o Gerenciamento de Telefones (Planilhas Telefones).

Lá a senha é armazenada como SHA256(salt + password) em hex, com salt aleatório por usuário.
"""
from __future__ import annotations

import hashlib


def hash_password_telefones_style(password: str, salt: str) -> str:
    """Mesmo algoritmo de `src.db.repository._hash_password` no projeto Telefones."""
    return hashlib.sha256((salt + password).encode("utf-8")).hexdigest()


def verify_password_telefones(plain_password: str, stored_hash: str, salt: str) -> bool:
    if not stored_hash or not salt:
        return False
    return hash_password_telefones_style(plain_password, salt) == stored_hash
