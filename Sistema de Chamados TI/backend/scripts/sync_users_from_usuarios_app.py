"""
Alinha a tabela `users` ao cadastro `usuarios_app` (Gerenciamento de Telefones):

- Cria/atualiza um `users` por linha em `usuarios_app` (via mesma logica do login).
- Remove usuarios sem vínculo com `usuarios_app` ou duplicados (mesmo snipe_user_id),
  reatribuindo FKs antes (chamados, comentarios, etc.).

Uso (pasta backend, venv ativado):

    python scripts/sync_users_from_usuarios_app.py --dry-run
    python scripts/sync_users_from_usuarios_app.py --yes

Requer PostgreSQL com `usuarios_app`.
"""
from __future__ import annotations

import argparse
import sys
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sqlalchemy import text
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.database import SessionLocal
from app.api.v1.endpoints.auth import upsert_chamados_user_from_usuario_app, _has_table
from app.models.user import User


def _is_postgres() -> bool:
    u = str(settings.DATABASE_URL or "")
    return u.startswith("postgresql") or "postgres" in u.lower()


def _pick_keeper_usuario_id(db: Session) -> int:
    row = db.execute(
        text(
            """
            SELECT id FROM usuarios_app
            WHERE ativo = TRUE
            ORDER BY is_admin DESC, id ASC
            LIMIT 1
            """
        )
    ).fetchone()
    if not row:
        row = db.execute(text("SELECT id FROM usuarios_app ORDER BY id ASC LIMIT 1")).fetchone()
    if not row:
        raise SystemExit("Nenhum usuario em usuarios_app.")
    return int(row[0])


def _reassign_all_fks(db: Session, from_id: int, to_id: int) -> None:
    """Move referencias de from_id -> to_id (mesmo usuario duplicado ou fallback)."""
    if from_id == to_id:
        return
    stmts = [
        "UPDATE tickets SET requester_id = :t WHERE requester_id = :f",
        "UPDATE tickets SET assigned_technician_id = :t WHERE assigned_technician_id = :f",
        "UPDATE comments SET user_id = :t WHERE user_id = :f",
        "UPDATE notifications SET user_id = :t WHERE user_id = :f",
        "UPDATE attachments SET user_id = :t WHERE user_id = :f",
        "UPDATE ticket_history SET user_id = :t WHERE user_id = :f",
        "UPDATE offboarding_logs SET user_id = :t WHERE user_id = :f",
        "UPDATE offboarding_logs SET created_by_id = :t WHERE created_by_id = :f",
        "UPDATE asset_assignments SET user_id = :t WHERE user_id = :f",
        "UPDATE asset_assignments SET assigned_by_id = :t WHERE assigned_by_id = :f",
    ]
    p = {"f": from_id, "t": to_id}
    for sql in stmts:
        try:
            db.execute(text(sql), p)
        except Exception as exc:
            print(f"  [aviso] {sql[:60]}... -> {exc}")


def _clear_optional_fks(db: Session, user_id: int) -> None:
    """Campos opcionais: zera apontando para usuario removido."""
    for sql in (
        "UPDATE tickets SET assigned_technician_id = NULL WHERE assigned_technician_id = :id",
        "UPDATE asset_assignments SET user_id = NULL WHERE user_id = :id",
        "UPDATE offboarding_logs SET user_id = NULL WHERE user_id = :id",
    ):
        try:
            db.execute(text(sql), {"id": user_id})
        except Exception:
            pass


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--yes", action="store_true", help="Executa alteracoes")
    parser.add_argument("--dry-run", action="store_true", help="So mostra o plano")
    args = parser.parse_args()

    if not _is_postgres():
        print("Use PostgreSQL (DATABASE_URL). Abortando.")
        sys.exit(1)

    db: Session = SessionLocal()
    try:
        if not _has_table(db, "usuarios_app"):
            print("Tabela usuarios_app nao encontrada.")
            sys.exit(1)

        rows = db.execute(
            text(
                """
                SELECT id, username, email, nome_exibicao, is_admin, ativo
                FROM usuarios_app ORDER BY id
                """
            )
        ).mappings().all()

        valid_uids = {int(r["id"]) for r in rows}
        print(f"usuarios_app: {len(valid_uids)} conta(s).")

        keeper_uid = _pick_keeper_usuario_id(db)
        print(f"Mantenedor (fallback FK): usuarios_app.id = {keeper_uid}")

        n_users = db.query(User).count()
        print(f"users (chamados) atualmente: {n_users} linha(s).")

        if args.dry_run:
            print("\n[--dry-run] Nada foi alterado. Execute com --yes para aplicar.")
            sys.exit(0)

        if not args.yes:
            print("\nPasse --yes para sincronizar e remover orfaos, ou --dry-run para só inspecionar.")
            sys.exit(0)

        # 1) Sincronizar cada usuario do Gerenciamento -> users
        for r in rows:
            upsert_chamados_user_from_usuario_app(db, dict(r))
        db.commit()

        keeper_user = db.query(User).filter(User.snipe_user_id == keeper_uid).first()
        if not keeper_user:
            raise RuntimeError("Usuario mantenedor nao encontrado em users apos sync.")
        keeper_id = keeper_user.id

        # 2) Mapa snipe_user_id -> [user ids]
        by_snipe: dict[int | None, list[int]] = defaultdict(list)
        for uid, snipe in db.query(User.id, User.snipe_user_id).all():
            by_snipe[snipe].append(uid)

        # 2a) Duplicatas: mesmo snipe_user_id -> mantem menor id
        for snipe, ids in list(by_snipe.items()):
            if snipe is None:
                continue
            ids = sorted(ids)
            if len(ids) <= 1:
                continue
            keep = ids[0]
            for extra in ids[1:]:
                print(f"Mesmo snipe_user_id={snipe}: fundindo users {extra} -> {keep}")
                _reassign_all_fks(db, extra, keep)
                db.execute(text("DELETE FROM users WHERE id = :id"), {"id": extra})
        db.commit()

        # Recarrega usuarios
        by_snipe = defaultdict(list)
        for uid, snipe in db.query(User.id, User.snipe_user_id).all():
            by_snipe[snipe].append(uid)

        # 2b) Orfaos: sem snipe ou snipe invalido -> FK para mantenedor e apaga
        orphan_ids = [
            uid
            for uid, snipe in db.query(User.id, User.snipe_user_id).all()
            if uid != keeper_id and (snipe is None or int(snipe) not in valid_uids)
        ]
        for uid in orphan_ids:
            print(f"Orfao/invalidez snipe: users.id={uid} -> reatribuir a mantenedor {keeper_id}")
            _clear_optional_fks(db, uid)
            _reassign_all_fks(db, uid, keeper_id)
            db.execute(text("DELETE FROM users WHERE id = :id"), {"id": uid})

        db.commit()
        remaining = db.query(User).count()
        print(f"Concluido. Restam {remaining} usuario(s) em users (vinculados ao Gerenciamento).")
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    main()
