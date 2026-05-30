"""Verifica convivência chamados (legado Streamlit) vs tickets (React) — Fase C2.

Uso:
    python -m scripts.verificar_chamados_legado
"""

from __future__ import annotations

import sys

from src.core.config import is_postgres_configured


def _fmt(label: str, value: object) -> None:
    print(f"  {label}: {value}")


def main() -> int:
    if not is_postgres_configured():
        print("DATABASE_URL não configurado. Use PostgreSQL unificado.")
        print("Guia: doc/SETUP_BANCO_LOCAL.md")
        return 1

    try:
        from src.db.repository import resumir_chamados_legado
    except ImportError as exc:
        print(f"Erro ao importar repositório: {exc}")
        return 1

    resumo = resumir_chamados_legado()

    print("Verificação C2 — chamados legado vs tickets (React)\n")
    _fmt("PostgreSQL", "sim" if resumo.get("postgres") else "não")
    _fmt("Tabela tickets", "OK" if resumo.get("tickets_existe") else "AUSENTE")
    print()
    _fmt("Registros em chamados (legado)", resumo.get("total_chamados", 0))
    _fmt("Registros em tickets (React)", resumo.get("total_tickets", 0))
    _fmt(
        "Chamados sem ticket com mesmo id",
        resumo.get("chamados_sem_ticket_mesmo_id", 0),
    )
    print()
    _fmt("Auditoria com chamado_id", resumo.get("auditoria_com_chamado_id", 0))
    _fmt("  -> apontando para tickets", resumo.get("auditoria_tickets", 0))
    _fmt("  -> so tabela legada chamados", resumo.get("auditoria_so_legado", 0))
    _fmt("  -> orfaos (id inexistente)", resumo.get("auditoria_orfa", 0))
    print()
    _fmt("Movimentacoes com chamado_id", resumo.get("movimentacoes_com_chamado_id", 0))
    _fmt("  -> so legado chamados", resumo.get("movimentacoes_so_legado", 0))
    _fmt("Eventos chamado_eventos", resumo.get("chamado_eventos", 0))

    print("\nConvenção (Fase C2):")
    print("  auditoria.chamado_id = tickets.id (React)")
    print("  Referências legadas em chamados.id continuam legíveis, com aviso na UI.")

    if not resumo.get("tickets_existe"):
        print("\nPróximo passo: alembic upgrade head no backend dos Chamados.")
        return 2

    legado = int(resumo.get("auditoria_so_legado") or 0)
    orfaos = int(resumo.get("auditoria_orfa") or 0)
    if legado or orfaos:
        print("\nAção sugerida (opcional):")
        print("  python -m scripts.migrar_chamados_para_tickets --dry-run")
        print("  python -m scripts.migrar_chamados_para_tickets --yes --remap-auditoria")
        print("\nDocumentação: doc/CHAMADOS_TICKETS_UNIFICACAO.md")
        return 0

    print("\nNenhum alerta crítico de auditoria legada.")
    print("Documentação: doc/CHAMADOS_TICKETS_UNIFICACAO.md")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
