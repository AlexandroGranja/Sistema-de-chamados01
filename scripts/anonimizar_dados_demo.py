"""
Anonimiza dados sensíveis no PostgreSQL para uso em repositório público / portfólio.

Substitui nomes, e-mails, telefones, IMEIs e referências corporativas reais por
valores fictícios determinísticos (mesmo original → mesmo fictício).

Uso:
  python -m scripts.anonimizar_dados_demo
  python -m scripts.anonimizar_dados_demo --dry-run
  python -m scripts.anonimizar_dados_demo --csv-only
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DOC = ROOT / "doc"

# Mapeamentos explícitos (nomes/equipes conhecidos do legado)
TEXT_REPLACEMENTS = [
    ("Prosper Distribuidora", "DemoCorp"),
    ("Nova Prosper", "Centro Alimentos"),
    ("Prosper Norte", "Distrito Norte"),
    ("Prosper Sul", "Distrito Sul"),
    ("PROSPER", "DEMOCORP"),
    ("Prosper", "DemoCorp"),
]

PERSON_REPLACEMENTS = {
    "Priscila Rangel Manhães": "Gestora Norte Demo",
    "Priscila Rangel Manhaes": "Gestora Norte Demo",
    "Gustavo Luis Dias De Armada": "Gestor Sul Demo",
    "Marcelo Neves": "Gestor Consumo Demo",
    "Marcelo Martins Da Costa": "Supervisor Oeste Demo",
    "Paulo Roberto Ferreira Chaves": "Supervisor Norte Demo",
    "Fabio Antonio Rosa Magalhaes": "Supervisor Niteroi Demo",
    "Fábio Antonio Rosa Magalhães": "Supervisor Niteroi Demo",
    "Marco Antonio Neves Suzart": "Gestor Especial Demo",
    "Ricardo Cascao": "Supervisor Especial Demo",
    "Ricardo Cascão": "Supervisor Especial Demo",
}

FIRST_NAMES = [
    "Ana", "Bruno", "Carla", "Daniel", "Elena", "Felipe", "Gabriela", "Henrique",
    "Isabela", "João", "Karina", "Lucas", "Mariana", "Nicolas", "Olivia", "Pedro",
    "Rafaela", "Samuel", "Tatiana", "Vitor",
]
LAST_NAMES = [
    "Almeida", "Barbosa", "Cardoso", "Dias", "Ferreira", "Gomes", "Henrique",
    "Lima", "Moura", "Nascimento", "Oliveira", "Pereira", "Queiroz", "Ribeiro",
    "Silva", "Teixeira", "Uchoa", "Vieira", "Xavier", "Zanetti",
]

DEMO_ADMIN_USER = "admin_demo"
DEMO_ADMIN_PASS = "Demo@2026!"
DEMO_OPERATOR_USER = "operador_demo"
DEMO_OPERATOR_PASS = "Demo@2026!"

PHONE_RE = re.compile(r"\b(\d{2})?\s*(\d{4,5})[-\s]?(\d{4})\b")
EMAIL_RE = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")


def _seed(key: str) -> int:
    return int(hashlib.sha256(key.encode("utf-8")).hexdigest()[:8], 16)


def _fake_name(original: str | None) -> str | None:
    if not original or not str(original).strip():
        return original
    raw = str(original).strip()
    for old, new in PERSON_REPLACEMENTS.items():
        if raw.lower() == old.lower():
            return new
    idx = _seed(f"name:{raw.lower()}")
    return f"{FIRST_NAMES[idx % len(FIRST_NAMES)]} {LAST_NAMES[(idx // len(FIRST_NAMES)) % len(LAST_NAMES)]}"


def _fake_phone(original: str | None) -> str | None:
    if not original or not str(original).strip():
        return original
    digits = re.sub(r"\D", "", str(original))
    if len(digits) < 8:
        return original
    idx = _seed(f"phone:{digits}") % 10000
    # Mantém DDD 21 quando existir; número fictício 90000-xxxx
    ddd = digits[:2] if len(digits) >= 10 else "21"
    return f"{ddd}90000{idx:04d}"


def _fake_email(original: str | None, prefix: str) -> str | None:
    if not original or not str(original).strip():
        return original
    idx = _seed(f"email:{original.lower()}") % 10000
    return f"{prefix}{idx}@demo.example"


def _fake_imei(original: str | None) -> str | None:
    if not original or not str(original).strip():
        return original
    idx = _seed(f"imei:{original}") % 10**15
    return f"{idx:015d}"[:15]


def _scrub_text(value: str | None) -> str | None:
    if value is None:
        return None
    text = str(value)
    for old, new in TEXT_REPLACEMENTS:
        text = text.replace(old, new)
    for old, new in PERSON_REPLACEMENTS.items():
        text = re.sub(re.escape(old), new, text, flags=re.IGNORECASE)

    def _phone_sub(m: re.Match) -> str:
        full = m.group(0)
        return _fake_phone(full) or full

    text = PHONE_RE.sub(_phone_sub, text)

    def _email_sub(m: re.Match) -> str:
        return _fake_email(m.group(0), "user") or m.group(0)

    text = EMAIL_RE.sub(_email_sub, text)
    return text


def _scrub_json(value) -> object | None:
    if value is None:
        return None
    if isinstance(value, (dict, list)):
        raw = json.dumps(value, ensure_ascii=False)
        cleaned = _scrub_text(raw)
        return json.loads(cleaned) if cleaned else value
    if isinstance(value, str):
        cleaned = _scrub_text(value)
        if cleaned and cleaned.strip().startswith(("{", "[")):
            try:
                return json.loads(cleaned)
            except json.JSONDecodeError:
                return cleaned
        return cleaned
    return value


def _anonymize_csv_file(path: Path, dry_run: bool) -> int:
    if not path.exists():
        print(f"  (skip) {path.name} — arquivo não encontrado")
        return 0
    rows: list[dict[str, str]] = []
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        fieldnames = reader.fieldnames or []
        for row in reader:
            new_row = {}
            for key, val in row.items():
                cleaned = _scrub_text(val) or ""
                if key.lower() in {"gestor", "supervisor", "gerente", "gestor_nome", "supervisor_nome"}:
                    cleaned = _fake_name(cleaned) or cleaned
                new_row[key] = cleaned
            rows.append(new_row)
    if dry_run:
        print(f"  [dry-run] {path.name}: {len(rows)} linhas")
        return len(rows)
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)
    print(f"  OK {path.name}: {len(rows)} linhas")
    return len(rows)


def anonymize_csv_configs(dry_run: bool) -> None:
    print("\n>> CSVs de configuração (doc/)")
    files = [
        DOC / "equipe_regras.csv",
        DOC / "equipes_alimento.csv",
        DOC / "equipes_medicamento.csv",
    ]
    for path in files:
        _anonymize_csv_file(path, dry_run)


def _upsert_demo_user(cur, username: str, password: str, is_admin: bool, nome: str) -> None:
    sys.path.insert(0, str(ROOT))
    from src.db.repository import _hash_password  # noqa: WPS433

    salt = hashlib.sha256(f"demo-salt-{username}".encode()).hexdigest()[:32]
    password_hash = _hash_password(password, salt)
    cur.execute(
        """
        INSERT INTO usuarios_app (username, email, nome_exibicao, password_hash, salt, auth_provider, is_admin, ativo)
        VALUES (%s, %s, %s, %s, %s, 'local', %s, TRUE)
        ON CONFLICT (username) DO UPDATE SET
            email = EXCLUDED.email,
            nome_exibicao = EXCLUDED.nome_exibicao,
            password_hash = EXCLUDED.password_hash,
            salt = EXCLUDED.salt,
            is_admin = EXCLUDED.is_admin,
            ativo = TRUE,
            atualizado_em = NOW()
        """,
        (
            username,
            f"{username}@demo.example",
            nome,
            password_hash,
            salt,
            is_admin,
        ),
    )


def anonymize_database(dry_run: bool) -> None:
    sys.path.insert(0, str(ROOT))
    from src.core.config import get_database_url, is_postgres_configured

    if not is_postgres_configured():
        print("DATABASE_URL não configurado. Copie .env.example para .env e tente novamente.")
        sys.exit(1)

    import psycopg
    from psycopg.rows import dict_row

    url = get_database_url()
    print(f"\n>> PostgreSQL: {url.split('@')[-1] if '@' in url else url}")

    with psycopg.connect(url, row_factory=dict_row) as conn:
        with conn.cursor() as cur:
            # colaboradores
            cur.execute("SELECT id, nome, nome_guerra, email, gestor_nome, supervisor_nome FROM colaboradores")
            cols = cur.fetchall()
            print(f"  colaboradores: {len(cols)}")
            if not dry_run:
                for row in cols:
                    cur.execute(
                        """
                        UPDATE colaboradores SET
                            nome = %s, nome_guerra = %s, email = %s,
                            gestor_nome = %s, supervisor_nome = %s, atualizado_em = NOW()
                        WHERE id = %s
                        """,
                        (
                            _fake_name(row["nome"]),
                            _fake_name(row.get("nome_guerra")),
                            _fake_email(row.get("email"), f"colab{row['id']}"),
                            _fake_name(row.get("gestor_nome")),
                            _fake_name(row.get("supervisor_nome")),
                            row["id"],
                        ),
                    )

            # equipes
            cur.execute("SELECT id, nome, gestor_nome, supervisor_nome, localidade FROM equipes")
            equipes = cur.fetchall()
            print(f"  equipes: {len(equipes)}")
            if not dry_run:
                for row in equipes:
                    cur.execute(
                        """
                        UPDATE equipes SET
                            nome = %s, gestor_nome = %s, supervisor_nome = %s,
                            localidade = %s, atualizado_em = NOW()
                        WHERE id = %s
                        """,
                        (
                            _scrub_text(row["nome"]),
                            _fake_name(row.get("gestor_nome")),
                            _fake_name(row.get("supervisor_nome")),
                            _scrub_text(row.get("localidade")),
                            row["id"],
                        ),
                    )

            # linhas — campos PII
            cur.execute(
                """
                SELECT id, numero_linha, linha, nome, email, gestor, supervisor,
                       nome_guerra, nome_usuario_snapshot, email_snapshot,
                       imei_a, imei_b, aba, aba_origem, observacao, motivo, localidade, equipe, equipe_padrao
                FROM linhas
                """
            )
            linhas = cur.fetchall()
            print(f"  linhas: {len(linhas)}")
            if not dry_run:
                for row in linhas:
                    new_num = _fake_phone(row.get("numero_linha") or row.get("linha"))
                    cur.execute(
                        """
                        UPDATE linhas SET
                            numero_linha = %s, linha = %s, nome = %s, email = %s,
                            gestor = %s, supervisor = %s, nome_guerra = %s,
                            nome_usuario_snapshot = %s, email_snapshot = %s,
                            imei_a = %s, imei_b = %s, aba = %s, aba_origem = %s,
                            observacao = %s, motivo = %s, localidade = %s,
                            equipe = %s, equipe_padrao = %s, atualizado_em = NOW()
                        WHERE id = %s
                        """,
                        (
                            new_num,
                            new_num,
                            _fake_name(row.get("nome")),
                            _fake_email(row.get("email"), f"linha{row['id']}"),
                            _fake_name(row.get("gestor")),
                            _fake_name(row.get("supervisor")),
                            _fake_name(row.get("nome_guerra")),
                            _fake_name(row.get("nome_usuario_snapshot")),
                            _fake_email(row.get("email_snapshot"), f"snap{row['id']}"),
                            _fake_imei(row.get("imei_a")),
                            _fake_imei(row.get("imei_b")),
                            _scrub_text(row.get("aba")),
                            _scrub_text(row.get("aba_origem")),
                            _scrub_text(row.get("observacao")),
                            _scrub_text(row.get("motivo")),
                            _scrub_text(row.get("localidade")),
                            _scrub_text(row.get("equipe")),
                            _scrub_text(row.get("equipe_padrao")),
                            row["id"],
                        ),
                    )

            # usuarios_app — renomear contas reais (exceto demo)
            cur.execute("SELECT id, username, email, nome_exibicao FROM usuarios_app")
            users = cur.fetchall()
            print(f"  usuarios_app: {len(users)}")
            if not dry_run:
                for row in users:
                    uname = (row["username"] or "").strip().lower()
                    if uname in {DEMO_ADMIN_USER, DEMO_OPERATOR_USER}:
                        continue
                    new_username = f"usuario_{row['id']}"
                    cur.execute(
                        """
                        UPDATE usuarios_app SET
                            username = %s, email = %s, nome_exibicao = %s, atualizado_em = NOW()
                        WHERE id = %s
                        """,
                        (
                            new_username,
                            _fake_email(row.get("email"), f"u{row['id']}"),
                            _fake_name(row.get("nome_exibicao") or row.get("username")),
                            row["id"],
                        ),
                    )

            # users (Chamados React)
            cur.execute(
                """
                SELECT EXISTS (
                    SELECT 1 FROM information_schema.tables
                    WHERE table_schema = 'public' AND table_name = 'users'
                )
                """
            )
            if cur.fetchone()["exists"]:
                cur.execute("SELECT id, name, email, phone FROM users")
                chamados_users = cur.fetchall()
                print(f"  users (Chamados): {len(chamados_users)}")
                if not dry_run:
                    for row in chamados_users:
                        cur.execute(
                            """
                            UPDATE users SET
                                name = %s, email = %s, phone = %s, updated_at = NOW()
                            WHERE id = %s
                            """,
                            (
                                _fake_name(row.get("name")),
                                _fake_email(row.get("email"), f"ch{row['id']}"),
                                _fake_phone(row.get("phone")),
                                row["id"],
                            ),
                        )

            # tickets
            cur.execute(
                """
                SELECT EXISTS (
                    SELECT 1 FROM information_schema.tables
                    WHERE table_schema = 'public' AND table_name = 'tickets'
                )
                """
            )
            if cur.fetchone()["exists"]:
                cur.execute(
                    "SELECT id, title, description, internal_notes, equipment_info, location FROM tickets"
                )
                tickets = cur.fetchall()
                print(f"  tickets: {len(tickets)}")
                if not dry_run:
                    for row in tickets:
                        cur.execute(
                            """
                            UPDATE tickets SET
                                title = %s, description = %s, internal_notes = %s,
                                equipment_info = %s, location = %s, updated_at = NOW()
                            WHERE id = %s
                            """,
                            (
                                _scrub_text(row.get("title")) or f"Ticket demo #{row['id']}",
                                _scrub_text(row.get("description")) or "Descrição fictícia para demonstração.",
                                _scrub_text(row.get("internal_notes")),
                                _scrub_text(row.get("equipment_info")),
                                _scrub_text(row.get("location")),
                                row["id"],
                            ),
                        )

            # auditoria
            cur.execute(
                "SELECT id, detalhes, antes_json, depois_json, username FROM auditoria"
            )
            audits = cur.fetchall()
            print(f"  auditoria: {len(audits)}")
            if not dry_run:
                for row in audits:
                    cur.execute(
                        """
                        UPDATE auditoria SET
                            detalhes = %s, antes_json = %s, depois_json = %s,
                            username = %s
                        WHERE id = %s
                        """,
                        (
                            _scrub_text(row.get("detalhes")),
                            json.dumps(_scrub_json(row.get("antes_json")), ensure_ascii=False)
                            if row.get("antes_json") is not None
                            else None,
                            json.dumps(_scrub_json(row.get("depois_json")), ensure_ascii=False)
                            if row.get("depois_json") is not None
                            else None,
                            _fake_name(row.get("username")) if row.get("username") else row.get("username"),
                            row["id"],
                        ),
                    )

            if not dry_run:
                _upsert_demo_user(cur, DEMO_ADMIN_USER, DEMO_ADMIN_PASS, True, "Administrador Demo")
                _upsert_demo_user(cur, DEMO_OPERATOR_USER, DEMO_OPERATOR_PASS, False, "Operador Demo")
                print(f"\n  Usuários demo: {DEMO_ADMIN_USER} / {DEMO_OPERATOR_USER} — senha: {DEMO_ADMIN_PASS}")

        if dry_run:
            print("\n[dry-run] Nenhuma alteração gravada.")
        else:
            conn.commit()
            print("\nAnonimização concluída.")


def main() -> int:
    parser = argparse.ArgumentParser(description="Anonimiza dados para portfólio público.")
    parser.add_argument("--dry-run", action="store_true", help="Mostra contagens sem gravar.")
    parser.add_argument("--csv-only", action="store_true", help="Só CSVs em doc/.")
    args = parser.parse_args()

    anonymize_csv_configs(args.dry_run)
    if not args.csv_only:
        anonymize_database(args.dry_run)

    print("\nPróximo passo: python -m scripts.sync_usuarios_chamados")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
