"""
Remove todos os usuarios do banco exceto suporte@prosperdistribuidora.com.br (ADMIN).

- Funciona com PostgreSQL (DATABASE_URL no backend/.env) ou SQLite (arquivo .db).
- Reatribui referencias (chamados, comentarios, etc.) para o usuario suporte antes de apagar.
- Define senha temporaria e papel ADMIN (altere a senha apos o login).

Uso (pasta backend, venv ativado):
  python scripts\\reset_usuarios_somente_suporte.py

SQLite por caminho de arquivo (opcional):
  python scripts\\reset_usuarios_somente_suporte.py "C:\\caminho\\chamados.db"

Variavel de ambiente (apenas modo SQLite arquivo):
  set CHAMADOS_DB=C:\\caminho\\chamados.db
"""
import os
import sqlite3
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from app.core.security import get_password_hash

KEEP_EMAIL = "suporte@prosperdistribuidora.com.br"
TEMP_PASSWORD = "Prosper2026!"  # altere apos o login


def _sqlite_file_path() -> Path | None:
    env = os.environ.get("CHAMADOS_DB")
    arg = sys.argv[1] if len(sys.argv) > 1 else None
    for p in (env, arg):
        if not p:
            continue
        path = Path(p)
        if path.suffix.lower() == ".db" or str(p).lower().endswith(".db"):
            return path
    return None


def _reset_sqlite_file(db_path: Path) -> None:
    print("Modo: SQLite arquivo ->", db_path)
    conn = sqlite3.connect(str(db_path))
    conn.execute("PRAGMA foreign_keys = ON")
    cur = conn.cursor()

    row = cur.execute(
        "SELECT id, email, name FROM users WHERE lower(trim(email)) = ?",
        (KEEP_EMAIL.lower().strip(),),
    ).fetchone()
    if not row:
        print("Usuario suporte nao encontrado; criando...")
        h = get_password_hash(TEMP_PASSWORD)
        cur.execute(
            """
            INSERT INTO users (name, email, password_hash, role, is_active)
            VALUES (?, ?, ?, 'ADMIN', 1)
            """,
            ("Alexandro Granja", KEEP_EMAIL, h),
        )
        keep_id = cur.lastrowid
        conn.commit()
        print("Criado suporte id", keep_id, "- removendo demais usuarios e reatribuindo FKs.")
    else:
        keep_id = row[0]

    print("Mantendo usuario id", keep_id, row or (keep_id, KEEP_EMAIL, "Alexandro Granja"))

    tables = _tables_fk()
    for table, col in tables:
        try:
            cur.execute("SELECT 1 FROM pragma_table_info(?) WHERE name = ?", (table, col))
            if cur.fetchone() is None:
                continue
            n = cur.execute(
                f"UPDATE {table} SET {col} = ? WHERE {col} IS NOT NULL AND {col} != ?",
                (keep_id, keep_id),
            ).rowcount
            if n:
                print(f"  {table}.{col}: reatribuidas {n} linhas")
        except sqlite3.OperationalError as e:
            print(f"  skip {table}.{col}: {e}")

    deleted = cur.execute("DELETE FROM users WHERE id != ?", (keep_id,)).rowcount
    print("Usuarios removidos:", deleted)

    h = get_password_hash(TEMP_PASSWORD)
    cur.execute(
        """
        UPDATE users
        SET role = 'ADMIN', is_active = 1, password_hash = ?,
            name = COALESCE(NULLIF(trim(name), ''), 'Administrador TI')
        WHERE id = ?
        """,
        (h, keep_id),
    )
    conn.commit()
    conn.close()
    print("Concluido. Login:", KEEP_EMAIL, "| Senha temporaria:", TEMP_PASSWORD)


def _tables_fk():
    return [
        ("tickets", "requester_id"),
        ("tickets", "assigned_technician_id"),
        ("comments", "user_id"),
        ("notifications", "user_id"),
        ("attachments", "user_id"),
        ("offboarding_logs", "user_id"),
        ("offboarding_logs", "created_by_id"),
        ("asset_assignments", "user_id"),
        ("asset_assignments", "assigned_by_id"),
        ("ticket_history", "user_id"),
    ]


def _reset_sqlalchemy() -> None:
    from sqlalchemy import inspect, text
    from sqlalchemy.orm import Session

    from app.core.database import SessionLocal, engine
    from app.models.user import User, UserRole

    safe_url = str(engine.url)
    if "@" in safe_url:
        safe_url = "..." + safe_url.split("@", 1)[-1]
    print("Modo: DATABASE_URL ->", safe_url)

    tables = _tables_fk()
    db: Session = SessionLocal()

    try:
        suporte = (
            db.query(User)
            .filter(User.email == KEEP_EMAIL)
            .first()
        )
        if not suporte:
            print("Usuario suporte nao encontrado; criando...")
            suporte = User(
                name="Alexandro Granja",
                email=KEEP_EMAIL,
                password_hash=get_password_hash(TEMP_PASSWORD),
                role=UserRole.ADMIN,
                is_active=True,
            )
            db.add(suporte)
            db.commit()
            db.refresh(suporte)
            print("Criado suporte id", suporte.id)
        keep_id = suporte.id
        print("Mantendo usuario id", keep_id, (keep_id, KEEP_EMAIL, suporte.name))

        conn = db.get_bind()
        insp = inspect(conn)
        existing = {t.lower() for t in insp.get_table_names()}

        for table, col in tables:
            if table.lower() not in existing:
                print(f"  skip {table}: tabela inexistente")
                continue
            cols = {c["name"].lower() for c in insp.get_columns(table)}
            if col.lower() not in cols:
                print(f"  skip {table}.{col}: coluna inexistente")
                continue
            sql = text(
                f"UPDATE {table} SET {col} = :kid WHERE {col} IS NOT NULL AND {col} != :kid"
            )
            r = db.execute(sql, {"kid": keep_id})
            if r.rowcount:
                print(f"  {table}.{col}: reatribuidas {r.rowcount} linhas")

        n = db.query(User).filter(User.id != keep_id).delete(synchronize_session=False)
        print("Usuarios removidos:", n)

        u = db.query(User).filter(User.id == keep_id).first()
        if u:
            u.password_hash = get_password_hash(TEMP_PASSWORD)
            u.role = UserRole.ADMIN
            u.is_active = True
            if not (u.name or "").strip():
                u.name = "Administrador TI"
        db.commit()
    finally:
        db.close()

    print("Concluido. Login:", KEEP_EMAIL, "| Senha temporaria:", TEMP_PASSWORD)


def main():
    sqlite_path = _sqlite_file_path()
    if sqlite_path is not None:
        if not sqlite_path.is_file():
            print("Arquivo nao encontrado:", sqlite_path)
            sys.exit(1)
        _reset_sqlite_file(sqlite_path)
    else:
        _reset_sqlalchemy()


if __name__ == "__main__":
    main()
