"""Teste C2: resumo legado, resolver/preparar referencia, pos-migracao."""

from __future__ import annotations

import sys


def main() -> int:
    from src.core.config import is_postgres_configured
    from src.db.repository import (
        preparar_referencia_chamado,
        resumir_chamados_legado,
        resolver_referencia_chamado,
    )

    if not is_postgres_configured():
        print("SKIP: DATABASE_URL nao configurado")
        return 0

    print("C2 — testes automatizados\n")

    resumo = resumir_chamados_legado()
    assert resumo.get("tickets_existe"), "tabela tickets ausente"
    print(f"[OK] tickets={resumo.get('total_tickets')} chamados_legado={resumo.get('total_chamados')}")
    print(f"[OK] auditoria_tickets={resumo.get('auditoria_tickets')} orfaos={resumo.get('auditoria_orfa')}")

    if int(resumo.get("total_tickets") or 0) > 0:
        ref = resolver_referencia_chamado("1")
        assert ref.get("valido"), f"ticket 1 deveria resolver: {ref}"
        assert ref.get("source") == "tickets", ref
        print("[OK] resolver_referencia_chamado('1') -> tickets")

    prep = preparar_referencia_chamado("999999")
    aviso = str(prep.get("aviso") or "").lower()
    assert not prep.get("valido"), prep
    assert "encontrado" in aviso, prep
    print("[OK] preparar_referencia_chamado stub desativado para id inexistente")

    legado = int(resumo.get("auditoria_so_legado") or 0)
    orfaos = int(resumo.get("auditoria_orfa") or 0)
    if legado or orfaos:
        print(f"[WARN] auditoria legado={legado} orfaos={orfaos}")
        return 1

    print("\nC2 PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
