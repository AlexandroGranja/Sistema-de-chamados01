"""Cria o banco PostgreSQL (se faltar) e aplica schema + migracoes do projeto."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path
from urllib.parse import urlsplit, urlunsplit

ROOT = Path(__file__).resolve().parent.parent
BACKEND = ROOT / "Sistema de Chamados TI" / "backend"


def _mask_url(url: str) -> str:
    parts = urlsplit(url)
    if parts.password:
        netloc = parts.netloc.replace(parts.password, "***")
        return urlunsplit((parts.scheme, netloc, parts.path, parts.query, parts.fragment))
    return url


def _admin_url(database_url: str, admin_db: str = "postgres") -> str:
    parts = urlsplit(database_url)
    return urlunsplit((parts.scheme, parts.netloc, f"/{admin_db}", parts.query, parts.fragment))


def _target_db_name(database_url: str) -> str:
    path = urlsplit(database_url).path.strip("/")
    if not path:
        raise ValueError("DATABASE_URL sem nome do banco.")
    return path


def _ensure_database(database_url: str) -> None:
    import psycopg
    from psycopg import sql

    db_name = _target_db_name(database_url)
    admin = _admin_url(database_url)
    print(f"Verificando banco '{db_name}'...")
    print(f"Admin: {_mask_url(admin)}")

    with psycopg.connect(admin, autocommit=True) as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT 1 FROM pg_database WHERE datname = %s", (db_name,))
            if cur.fetchone():
                print(f"Banco '{db_name}' ja existe.")
                return
            cur.execute(
                sql.SQL("CREATE DATABASE {} ENCODING 'UTF8' TEMPLATE template0").format(
                    sql.Identifier(db_name)
                )
            )
            print(f"Banco '{db_name}' criado.")


def _run_module(module: str) -> None:
    print(f"\n>> python -m {module}")
    subprocess.run([sys.executable, "-m", module], cwd=ROOT, check=True)


def _run_alembic() -> None:
    alembic = BACKEND / ("Scripts" if sys.platform == "win32" else "bin") / "alembic.exe"
    if not alembic.exists():
        alembic = BACKEND / "venv" / "Scripts" / "alembic.exe"
    if not alembic.exists():
        raise FileNotFoundError(
            "Alembic nao encontrado. Instale deps do backend:\n"
            f'  cd "{BACKEND}"\n'
            "  python -m venv venv\n"
            "  .\\venv\\Scripts\\pip install -r requirements.txt"
        )
    print(f"\n>> {alembic} upgrade head")
    subprocess.run([str(alembic), "upgrade", "head"], cwd=BACKEND, check=True)


def main() -> int:
    sys.path.insert(0, str(ROOT))
    from src.core.config import get_database_url, is_postgres_configured

    if not is_postgres_configured():
        print("DATABASE_URL nao configurado em .env")
        return 1

    database_url = get_database_url()
    try:
        _ensure_database(database_url)
        _run_module("scripts.init_postgres")
        if BACKEND.exists():
            _run_alembic()
        _run_module("scripts.verificar_banco")
    except Exception as exc:
        print(f"\nFalha: {exc}")
        print("\nSe a autenticacao falhou:")
        print("- Confirme a senha do usuario postgres no pgAdmin (Register Server)")
        print("- Atualize DATABASE_URL no .env (senha com $ use %24 ou aspas)")
        print("- Guia: doc/SETUP_BANCO_LOCAL.md")
        return 1

    print("\nSetup concluido.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
