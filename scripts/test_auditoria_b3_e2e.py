"""Teste E2E B3: API /telefones/* grava auditoria com ticket_id."""

from __future__ import annotations

import json
import os
import sys
import uuid

import requests
from dotenv import load_dotenv

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

load_dotenv(os.path.join(ROOT, ".env"))

API_BASE = os.environ.get("CHAMADOS_API_URL", "http://127.0.0.1:8000").rstrip("/")
LOGIN_USER = os.environ.get("E2E_LOGIN_USER", "alexandro granja")
LOGIN_PASS = os.environ.get("E2E_LOGIN_PASS", "")


def _db_conn():
    from src.db.repository import get_connection

    return get_connection()


def _ensure_api() -> None:
    probes = ("/docs", "/openapi.json", "/api/auth/login")
    last_exc = None
    for path in probes:
        try:
            r = requests.get(f"{API_BASE}{path}", timeout=8)
            if r.status_code in (200, 405, 422):
                return
        except Exception as exc:
            last_exc = exc
    raise SystemExit(
        f"API nao responde em {API_BASE} ({last_exc}). "
        "Suba com ativador_completo.bat ou uvicorn na porta 8000."
    )


def _login() -> str:
    if not LOGIN_PASS:
        raise SystemExit(
            "Defina E2E_LOGIN_PASS no ambiente ou passe como 2o argumento: "
            "python -m scripts.test_auditoria_b3_e2e <senha>"
        )
    r = requests.post(
        f"{API_BASE}/api/auth/login",
        json={"email": LOGIN_USER, "password": LOGIN_PASS},
        timeout=30,
    )
    if r.status_code != 200:
        raise SystemExit(f"Login falhou ({r.status_code}): {r.text[:500]}")
    token = r.json().get("access_token")
    if not token:
        raise SystemExit("Login OK mas sem access_token.")
    return token


def _pick_vago_line(cur) -> tuple[int, str]:
    def _query() -> tuple[int, str] | None:
        cur.execute(
            """
            SELECT id, COALESCE(numero_linha, linha) AS nl
            FROM linhas
            WHERE modo = 'ativas'
              AND upper(trim(coalesce(nome, ''))) = 'VAGO'
              AND COALESCE(numero_linha, linha) IS NOT NULL
              AND trim(COALESCE(numero_linha, linha)) <> ''
            ORDER BY id DESC
            LIMIT 1
            """
        )
        row = cur.fetchone()
        if not row:
            return None
        return int(row[0]), str(row[1]).strip()

    found = _query()
    if found:
        return found

    cur.execute(
        """
        UPDATE linhas SET nome = 'VAGO', codigo = 'VAGO'
        WHERE id = (
            SELECT id FROM linhas
            WHERE modo = 'ativas' AND nome ILIKE 'Colaborador E2E%'
            ORDER BY id DESC LIMIT 1
        )
        RETURNING id
        """
    )
    if cur.fetchone():
        cur.connection.commit()

    found = _query()
    if found:
        return found
    raise SystemExit("Nenhuma linha VAGO encontrada para teste de onboarding.")


def _create_ticket(cur, user_app_id: int) -> int:
    """Cria ticket real em `tickets` (Fase C2 — nao usar tabela legada `chamados`)."""
    suffix = uuid.uuid4().hex[:8]
    titulo = f"E2E B3 auditoria {suffix}"
    cur.execute(
        "SELECT id FROM users WHERE snipe_user_id = %s ORDER BY id LIMIT 1",
        (user_app_id,),
    )
    row = cur.fetchone()
    if not row:
        raise SystemExit(
            f"Usuario sem espelho em users (snipe_user_id={user_app_id}). "
            "Rode: python -m scripts.sync_usuarios_chamados"
        )
    requester_id = int(row[0])
    cur.execute(
        """
        INSERT INTO tickets (
            ticket_number, title, description,
            ticket_type, priority, status, requester_id,
            category, subcategory, internal_notes
        )
        VALUES (
            'TMP', %s, 'Teste automatico B3 auditoria API',
            'REQUEST'::tickettype, 'MEDIUM'::ticketpriority, 'OPEN'::ticketstatus, %s,
            'TI', 'Onboarding', %s
        )
        RETURNING id
        """,
        (titulo, requester_id, f"[e2e-b3-{suffix}]"),
    )
    ticket_id = int(cur.fetchone()[0])
    cur.execute(
        "UPDATE tickets SET ticket_number = %s WHERE id = %s",
        (str(ticket_id), ticket_id),
    )
    cur.connection.commit()
    return ticket_id


def _user_app_id(cur) -> int:
    cur.execute(
        """
        SELECT id FROM usuarios_app
        WHERE lower(trim(username)) = lower(trim(%s))
        LIMIT 1
        """,
        (LOGIN_USER,),
    )
    row = cur.fetchone()
    if not row:
        raise SystemExit(f"Usuario '{LOGIN_USER}' nao encontrado em usuarios_app.")
    return int(row[0])


def _count_auditoria_before(cur, ticket_id: int) -> int:
    cur.execute(
        "SELECT COUNT(*) FROM auditoria WHERE chamado_id = %s AND acao = 'onboarding_linha'",
        (ticket_id,),
    )
    return int(cur.fetchone()[0])


def main() -> int:
    if len(sys.argv) > 1 and sys.argv[1].strip():
        global LOGIN_PASS
        LOGIN_PASS = sys.argv[1].strip()

    print(f"API: {API_BASE}")
    _ensure_api()
    token = _login()
    headers = {"Authorization": f"Bearer {token}"}

    conn = _db_conn()
    try:
        with conn.cursor() as cur:
            user_id = _user_app_id(cur)
            linha_id, numero_linha = _pick_vago_line(cur)
            ticket_id = _create_ticket(cur, user_id)
            before = _count_auditoria_before(cur, ticket_id)

            test_name = f"Colaborador E2E {uuid.uuid4().hex[:6]}"
            payload = {
                "numero_linha": numero_linha,
                "nome": test_name,
                "codigo": "E2E001",
                "cargo": "Analista E2E",
                "setor": "TI",
                "equipe": "Suporte",
                "ticket_id": ticket_id,
            }
            print(f"Linha VAGO id={linha_id} numero={numero_linha}")
            print(f"Ticket chamado_id={ticket_id}")
            print(f"Auditoria onboarding_linha antes: {before}")

        r = requests.post(
            f"{API_BASE}/api/telefones/onboarding",
            headers=headers,
            json=payload,
            timeout=60,
        )
        print(f"POST /onboarding -> {r.status_code}")
        if r.status_code != 200:
            print(r.text[:800])
            return 1
        print("Resposta:", r.json().get("mensagem", r.json()))

        with conn.cursor() as cur:
            after = _count_auditoria_before(cur, ticket_id)
            cur.execute(
                """
                SELECT id, acao, chamado_id, username, origem, detalhes,
                       LEFT(COALESCE(depois_json::text, ''), 120) AS depois_preview
                FROM auditoria
                WHERE chamado_id = %s AND acao = 'onboarding_linha'
                ORDER BY id DESC
                LIMIT 1
                """,
                (ticket_id,),
            )
            row = cur.fetchone()

        if after <= before or not row:
            print("FALHA: nenhum registro novo em auditoria.")
            return 1

        audit_id, acao, chamado_id, username, origem, detalhes, depois_preview = row
        print("\n=== AUDITORIA OK ===")
        print(f"id={audit_id} acao={acao} chamado_id={chamado_id}")
        print(f"username={username!r} origem={origem!r}")
        print(f"detalhes={detalhes!r}")
        print(f"depois_json preview={depois_preview!r}...")

        depois_full = None
        with conn.cursor() as cur:
            cur.execute("SELECT depois_json FROM auditoria WHERE id = %s", (audit_id,))
            depois_full = cur.fetchone()[0]
        if depois_full:
            data = depois_full if isinstance(depois_full, dict) else json.loads(depois_full)
            alteracoes = data.get("alteracoes") or []
            print(f"alteracoes_total={data.get('alteracoes_total')} campos={len(alteracoes)}")
            if alteracoes:
                ch = alteracoes[0]
                print(f"  exemplo: {ch.get('campo')}: {ch.get('antes')} -> {ch.get('depois')}")

        print("\nE2E B3 PASS")
        return 0
    finally:
        conn.close()


if __name__ == "__main__":
    raise SystemExit(main())
