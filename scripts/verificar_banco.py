"""Verifica conexão PostgreSQL e orienta próximos passos de setup local."""

from __future__ import annotations

import sys
from urllib.parse import urlsplit

from src.core.config import get_database_url, is_postgres_configured


def _mask_url(url: str) -> str:
    try:
        parts = urlsplit(url)
        if parts.password:
            netloc = parts.netloc.replace(parts.password, "***")
            return parts._replace(netloc=netloc).geturl()
        return url
    except Exception:
        return url


def main() -> int:
    if not is_postgres_configured():
        print("DATABASE_URL nao configurado.")
        print("1. Copie .env.example para .env na raiz do projeto")
        print("2. Ajuste usuario, senha, host e nome do banco")
        print("3. Use o MESMO DATABASE_URL em Sistema de Chamados TI/backend/.env")
        print("Guia: doc/SETUP_BANCO_LOCAL.md")
        return 1

    url = get_database_url()
    print(f"Conexao: {_mask_url(url)}")

    try:
        from src.db.repository import get_connection
    except ImportError as exc:
        print(f"Erro ao importar repositório: {exc}")
        return 1

    expected = {
        "usuarios_app": "Gerenciamento (login)",
        "linhas": "Gerenciamento (linhas)",
        "chamados": "Chamados legado Streamlit",
        "auditoria": "Auditoria unificada",
        "tickets": "Chamados React (Fase B1)",
        "users": "Chamados React (usuarios API)",
    }

    try:
        conn = get_connection()
        with conn.cursor() as cur:
            cur.execute("SELECT version()")
            version = cur.fetchone()[0]
            print(f"PostgreSQL: {version.split(',')[0]}")

            cur.execute(
                """
                SELECT tablename
                FROM pg_tables
                WHERE schemaname = 'public'
                ORDER BY tablename
                """
            )
            tables = {row[0] for row in cur.fetchall()}
    except Exception as exc:
        err = str(exc).encode("ascii", "replace").decode("ascii")
        print(f"Falha ao conectar: {err}")
        print("\nVerifique:")
        print("- PostgreSQL rodando no PC (servico ou Docker)")
        print("- Host/porta corretos (padrao localhost:5432)")
        print("- Usuario/senha e nome do banco existentes")
        print("Guia: doc/SETUP_BANCO_LOCAL.md")
        return 1
    finally:
        try:
            conn.close()
        except Exception:
            pass

    print("\nTabelas esperadas:")
    missing_required = []
    for table, desc in expected.items():
        status = "OK" if table in tables else "AUSENTE"
        print(f"  [{status}] {table} — {desc}")
        if table in {"usuarios_app", "linhas", "auditoria"} and table not in tables:
            missing_required.append(table)

    print("\nProximos passos sugeridos:")
    if missing_required:
        print("  python -m scripts.init_postgres")
    if "tickets" not in tables:
        print("  cd \"Sistema de Chamados TI/backend\"")
        print("  alembic upgrade head")
    if not missing_required and "tickets" in tables:
        print("  Banco pronto para dev. Execute ativador_completo.bat")
    print("\nDocumentacao: doc/SETUP_BANCO_LOCAL.md")
    return 0 if not missing_required else 2


if __name__ == "__main__":
    raise SystemExit(main())
