"""Migra registros legados `chamados` → `tickets` (one-shot, Fase C2).

Por padrão roda em dry-run. Use --yes para gravar.

Uso:
    python -m scripts.migrar_chamados_para_tickets --dry-run
    python -m scripts.migrar_chamados_para_tickets --yes
    python -m scripts.migrar_chamados_para_tickets --yes --remap-auditoria
"""

from __future__ import annotations

import argparse
import sys
from typing import Any, Optional

from src.core.config import is_postgres_configured

_MAP_TIPO = {
    "gerenciamento": "REQUEST",
    "incidente": "INCIDENT",
    "solicitacao": "REQUEST",
    "manutencao": "MAINTENANCE",
    "roubo_perda": "INCIDENT",
}

_MAP_STATUS = {
    "aberto": "OPEN",
    "em_andamento": "IN_PROGRESS",
    "aguardando": "WAITING_USER",
    "resolvido": "RESOLVED",
    "fechado": "CLOSED",
}

_MAP_PRIORIDADE = {
    "baixa": "LOW",
    "normal": "MEDIUM",
    "alta": "HIGH",
    "critica": "CRITICAL",
}


def _map_val(raw: str, mapping: dict[str, str], default: str) -> str:
    key = str(raw or "").strip().lower()
    return mapping.get(key, default)


def _default_requester_id(cur) -> Optional[int]:
    cur.execute(
        """
        SELECT id FROM users
        WHERE role::text ILIKE 'admin'
        ORDER BY id
        LIMIT 1
        """
    )
    row = cur.fetchone()
    if row:
        return int(row[0])
    cur.execute("SELECT id FROM users ORDER BY id LIMIT 1")
    row = cur.fetchone()
    return int(row[0]) if row else None


def _resolve_requester_id(cur, solicitante_id: Any, fallback_id: Optional[int]) -> Optional[int]:
    if solicitante_id is not None:
        cur.execute(
            "SELECT id FROM users WHERE snipe_user_id = %s ORDER BY id LIMIT 1",
            (int(solicitante_id),),
        )
        row = cur.fetchone()
        if row:
            return int(row[0])
    return fallback_id


def _ticket_exists(cur, chamado_id: int, numero: str) -> bool:
    cur.execute("SELECT 1 FROM tickets WHERE id = %s LIMIT 1", (chamado_id,))
    if cur.fetchone():
        return True
    leg_num = f"LEG-{numero}"
    cur.execute(
        "SELECT 1 FROM tickets WHERE ticket_number IN (%s, %s) LIMIT 1",
        (str(numero), leg_num),
    )
    return cur.fetchone() is not None


def executar_migracao(
    *,
    dry_run: bool = True,
    remap_auditoria: bool = False,
    limit: int = 500,
) -> tuple[int, int, list[str]]:
    from src.db.repository import _tickets_table_exists, get_connection

    conn = get_connection()
    migrados = 0
    pulados = 0
    log: list[str] = []
    try:
        with conn.cursor() as cur:
            if not _tickets_table_exists(cur):
                raise RuntimeError("Tabela tickets ausente. Rode alembic upgrade head.")

            fallback_requester = _default_requester_id(cur)
            if fallback_requester is None:
                raise RuntimeError(
                    "Nenhum usuário em `users`. Rode sync: python -m scripts.sync_usuarios_chamados"
                )

            cur.execute(
                """
                SELECT
                    c.id,
                    c.numero_chamado,
                    c.tipo,
                    c.status,
                    c.prioridade,
                    c.titulo,
                    c.descricao,
                    c.category,
                    c.location,
                    c.equipment_info,
                    c.internal_notes,
                    c.solicitante_id,
                    c.aberto_em,
                    c.atualizado_em,
                    c.fechado_em
                FROM chamados c
                ORDER BY c.id
                LIMIT %s
                """,
                (max(1, int(limit)),),
            )
            rows = cur.fetchall()

            for row in rows:
                chamado_id = int(row[0])
                numero = str(row[1] or chamado_id)
                if _ticket_exists(cur, chamado_id, numero):
                    pulados += 1
                    continue

                ticket_number = f"LEG-{numero}"
                title = str(row[5] or f"Chamado legado #{numero}")[:255]
                description = str(row[6] or title or "Migrado da tabela chamados.")
                ticket_type = _map_val(row[2], _MAP_TIPO, "REQUEST")
                status = _map_val(row[3], _MAP_STATUS, "OPEN")
                priority = _map_val(row[4], _MAP_PRIORIDADE, "MEDIUM")
                requester_id = _resolve_requester_id(cur, row[11], fallback_requester)
                if requester_id is None:
                    log.append(f"SKIP chamado {chamado_id}: sem requester_id")
                    pulados += 1
                    continue

                internal_notes = str(row[10] or "").strip()
                marker = f"[migrado-chamado-id={chamado_id}]"
                if marker not in internal_notes:
                    internal_notes = f"{marker}\n{internal_notes}".strip()

                if dry_run:
                    log.append(
                        f"DRY chamado {chamado_id} -> ticket {ticket_number} "
                        f"({ticket_type}/{status}/{priority})"
                    )
                    migrados += 1
                    continue

                cur.execute(
                    """
                    INSERT INTO tickets (
                        ticket_number, title, description,
                        ticket_type, priority, status,
                        requester_id, category, location, equipment_info, internal_notes,
                        created_at, updated_at, resolved_at, closed_at
                    )
                    VALUES (
                        %s, %s, %s,
                        %s::tickettype, %s::ticketpriority, %s::ticketstatus,
                        %s, %s, %s, %s, %s,
                        %s, %s, %s, %s
                    )
                    RETURNING id
                    """,
                    (
                        ticket_number,
                        title,
                        description,
                        ticket_type,
                        priority,
                        status,
                        requester_id,
                        row[7],
                        row[8],
                        row[9],
                        internal_notes or None,
                        row[12],
                        row[13],
                        row[14] if status == "RESOLVED" else None,
                        row[14] if status == "CLOSED" else None,
                    ),
                )
                new_ticket_id = int(cur.fetchone()[0])
                migrados += 1
                log.append(
                    f"OK chamado {chamado_id} -> ticket id={new_ticket_id} num={ticket_number}"
                )

                if remap_auditoria:
                    cur.execute(
                        "UPDATE auditoria SET chamado_id = %s WHERE chamado_id = %s",
                        (new_ticket_id, chamado_id),
                    )
                    cur.execute(
                        "UPDATE movimentacoes_linha SET chamado_id = %s WHERE chamado_id = %s",
                        (new_ticket_id, chamado_id),
                    )

            if not dry_run:
                conn.commit()
    finally:
        conn.close()

    return migrados, pulados, log


def main() -> int:
    parser = argparse.ArgumentParser(description="Migrar chamados legado → tickets (C2)")
    parser.add_argument("--dry-run", action="store_true", help="Simula sem gravar (padrão)")
    parser.add_argument("--yes", action="store_true", help="Executa gravação")
    parser.add_argument(
        "--remap-auditoria",
        action="store_true",
        help="Atualiza auditoria/movimentacoes_linha para o novo tickets.id",
    )
    parser.add_argument("--limit", type=int, default=500, help="Máximo de chamados por execução")
    args = parser.parse_args()

    if not is_postgres_configured():
        print("DATABASE_URL não configurado.")
        return 1

    dry_run = not args.yes
    if dry_run and not args.dry_run and not args.yes:
        dry_run = True

    try:
        migrados, pulados, log = executar_migracao(
            dry_run=dry_run,
            remap_auditoria=args.remap_auditoria,
            limit=args.limit,
        )
    except Exception as exc:
        print(f"Falha: {exc}")
        return 1

    modo = "DRY-RUN" if dry_run else "EXECUTADO"
    print(f"Migração C2 — {modo}\n")
    print(f"  Migrados/simulados: {migrados}")
    print(f"  Pulados (já existiam): {pulados}")
    if args.remap_auditoria and not dry_run:
        print("  Remapeamento auditoria/movimentações: sim")
    if log:
        print("\nDetalhes:")
        for line in log[:80]:
            print(f"  {line}")
        if len(log) > 80:
            print(f"  ... +{len(log) - 80} linhas")
    if dry_run:
        print("\nPara gravar: python -m scripts.migrar_chamados_para_tickets --yes")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
