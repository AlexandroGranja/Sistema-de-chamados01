import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Optional, Tuple
import logging
import unicodedata
import os

from app.schemas.ticket import OffboardingAction
from app.core.config import settings
from app.core.database import engine
from app.services.auditoria import audit_linha_create, audit_linha_update, fetch_linha_snapshot
from sqlalchemy import text

logger = logging.getLogger(__name__)


MAINTENANCE_ACTIONS = {
    OffboardingAction.OFFBOARDING_WITH_MAINTENANCE.value,
    OffboardingAction.MAINTENANCE_ONLY.value,
}


def _normalize(value: str) -> str:
    return (value or "").strip().lower()


def _normalize_key(value: str) -> str:
    text = (value or "").strip().lower()
    text = "".join(
        ch for ch in unicodedata.normalize("NFD", text) if unicodedata.category(ch) != "Mn"
    )
    return " ".join(text.split())


def _append_note(current_note: str, message: str) -> str:
    base = (current_note or "").strip()
    if not base:
        return message
    return f"{base} | {message}"


def _find_rows(conn: sqlite3.Connection, employee_name: str, asset_tag: str) -> list[sqlite3.Row]:
    name = _normalize(employee_name)
    name_key = _normalize_key(employee_name)
    tag = (asset_tag or "").strip()
    base_sql = (
        "SELECT id, nome, linha, equipe, equipe_padrao, segmento, papel, gestor, supervisor, observacao "
        "FROM linhas WHERE modo = 'ativas' "
    )

    # 1) Prioriza identificação por ativo/linha/código (mais confiável que nome).
    if tag:
        by_tag = conn.execute(
            base_sql + "AND (patrimonio = ? OR codigo = ? OR linha = ?)",
            (tag, tag, tag),
        ).fetchall()
        if by_tag:
            return by_tag

    # 2) Match direto por nome.
    by_name = conn.execute(base_sql + "AND lower(trim(nome)) = ?", (name,)).fetchall()
    if by_name:
        return by_name

    # 3) Fallback acento-insensível.
    candidates = conn.execute(base_sql + "AND nome IS NOT NULL AND trim(nome) <> ''").fetchall()
    return [r for r in candidates if _normalize_key(r["nome"]) == name_key]


def _sync_team_leadership_if_needed(conn: sqlite3.Connection, row: sqlite3.Row, employee_name: str) -> None:
    team = (row["equipe_padrao"] or "").strip()
    segment = (row["segmento"] or "").strip()
    if not team or not segment:
        return

    role = _normalize(row["papel"] or "")
    if role == "gerente":
        conn.execute(
            """
            UPDATE linhas
            SET gestor = 'Vago'
            WHERE modo = 'ativas'
              AND equipe_padrao = ?
              AND segmento = ?
              AND lower(trim(coalesce(gestor, ''))) = lower(trim(?))
            """,
            (team, segment, employee_name),
        )
    if role == "supervisor":
        conn.execute(
            """
            UPDATE linhas
            SET supervisor = 'Vago'
            WHERE modo = 'ativas'
              AND equipe_padrao = ?
              AND segmento = ?
              AND lower(trim(coalesce(supervisor, ''))) = lower(trim(?))
            """,
            (team, segment, employee_name),
        )


def _get_table_columns(conn: sqlite3.Connection) -> set[str]:
    rows = conn.execute("PRAGMA table_info(linhas)").fetchall()
    return {str(r["name"]) for r in rows}


def _validate_required_schema(conn: sqlite3.Connection) -> Optional[str]:
    required = {"id", "nome", "linha", "segmento", "equipe_padrao", "modo"}
    cols = _get_table_columns(conn)
    missing = sorted(required - cols)
    if missing:
        return f"Schema inválido em linhas. Colunas ausentes: {', '.join(missing)}."
    return None


def _create_maintenance_copy(
    conn: sqlite3.Connection,
    row: sqlite3.Row,
    employee_name: str,
    asset_tag: str,
    reason: str,
    return_date: str,
    ticket_id: int | None,
) -> None:
    source = conn.execute("SELECT * FROM linhas WHERE id = ?", (row["id"],)).fetchone()
    if not source:
        return

    maintenance_segment, maintenance_group, maintenance_team = _get_maintenance_labels(conn)
    ticket_suffix = f" [ticket_id={ticket_id}]" if ticket_id else ""
    duplicate = conn.execute(
        "SELECT id FROM linhas WHERE observacao LIKE ? ORDER BY id DESC LIMIT 1",
        (f"%{ticket_suffix}%",),
    ).fetchone()
    if duplicate:
        return

    now = datetime.now()
    base_date = (return_date or "").strip()
    event_date = base_date or now.strftime("%Y-%m-%d")
    # Usamos timestamp completo para manter ordenação correta (recente -> antigo) no segmento manutenção.
    event_timestamp = f"{event_date} {now.strftime('%H:%M:%S')}"
    note = (
        f"Cópia criada para manutenção via desligamento ({employee_name})"
        f"{ticket_suffix}. Data: {event_date}"
    )
    if reason:
        note = f"{note}. Motivo: {reason}"
    new_obs = _append_note(source["observacao"], note)

    data = dict(source)
    data.pop("id", None)
    data.pop("criado_em", None)
    data["segmento"] = maintenance_segment
    data["grupo_equipe"] = maintenance_group
    data["equipe_padrao"] = maintenance_team
    data["equipe"] = maintenance_team
    data["tipo_equipe"] = "Interna"
    data["localidade"] = maintenance_team
    data["modo"] = "ativas"
    data["observacao"] = new_obs
    source_line = (str(source["linha"]) if source["linha"] is not None else "").strip()
    # Evita colisão de chave lógica no app de gerenciamento: cópia de manutenção usa linha única.
    if source_line:
        data["linha"] = f"MNT-{source_line}-{ticket_id or source['id']}"
    if asset_tag.strip():
        data["patrimonio"] = asset_tag.strip()
        if not (str(data.get("codigo") or "").strip()):
            data["codigo"] = asset_tag.strip()
    if "data_troca" in data:
        data["data_troca"] = event_timestamp
    if "data_ocorrencia" in data:
        data["data_ocorrencia"] = event_timestamp

    cols = _get_table_columns(conn)
    payload = {k: v for k, v in data.items() if k in cols}
    keys = list(payload.keys())
    placeholders = ", ".join("?" for _ in keys)
    columns = ", ".join(keys)
    values = [payload[k] for k in keys]
    conn.execute(f"INSERT INTO linhas ({columns}) VALUES ({placeholders})", values)


def _apply_maintenance_original(
    conn: sqlite3.Connection,
    row: sqlite3.Row,
    employee_name: str,
    reason: str,
    return_date: str,
    ticket_id: int | None,
) -> None:
    event_date = (return_date or "").strip() or datetime.now().strftime("%Y-%m-%d")
    ticket_suffix = f" [ticket_id={ticket_id}]" if ticket_id else ""
    note = (
        f"Linha original mantida na equipe e marcada como manutenção "
        f"após desligamento ({employee_name}){ticket_suffix}. Data: {event_date}"
    )
    if reason:
        note = f"{note}. Motivo: {reason}"
    new_obs = _append_note(row["observacao"], note)

    conn.execute(
        """
        UPDATE linhas
        SET nome = ?,
            nome_guerra = ?,
            papel = ?,
            observacao = ?,
            modo = 'ativas'
        WHERE id = ?
        """,
        (
            "Manutenção",
            "Manutenção",
            "Manutenção",
            new_obs,
            row["id"],
        ),
    )


def _apply_vacancy(conn: sqlite3.Connection, row: sqlite3.Row, employee_name: str) -> None:
    note = f"Linha marcada como vaga automaticamente via desligamento ({employee_name})"
    new_obs = _append_note(row["observacao"], note)

    conn.execute(
        """
        UPDATE linhas
        SET nome = ?,
            nome_guerra = ?,
            observacao = ?,
            gestor = ?,
            supervisor = ?
        WHERE id = ?
        """,
        ("VAGO", "VAGO", new_obs, "", "", row["id"]),
    )


def _get_maintenance_labels(conn: sqlite3.Connection) -> Tuple[str, str, str]:
    """
    Usa o mesmo rótulo de manutenção já existente no banco de telefonia
    para evitar divergência com filtros do sistema.
    """
    existing = conn.execute(
        """
        SELECT segmento
        FROM linhas
        WHERE lower(coalesce(segmento, '')) LIKE 'manuten%'
           OR lower(coalesce(grupo_equipe, '')) LIKE 'manuten%'
           OR lower(coalesce(equipe_padrao, '')) LIKE 'manuten%'
        ORDER BY id DESC
        LIMIT 1
        """
    ).fetchone()
    if existing:
        segmento = (existing["segmento"] or "").strip() or "Manutenção"
        return segmento, segmento, segmento
    return "Manutenção", "Manutenção", "Manutenção"


def sync_offboarding_to_telefones(
    *,
    enabled: bool,
    db_path: str,
    employee_name: str,
    asset_tag: str,
    action: str,
    maintenance_reason: str = "",
    return_date: str = "",
    ticket_id: int | None = None,
    audit_user_id: Optional[int] = None,
    audit_username: Optional[str] = None,
) -> Tuple[bool, str]:
    """
    Sincroniza desligamento do chamado para o banco do Gerenciamento de Telefones.

    Regras:
    - Ações de manutenção -> mantém linha original (nome=Manutenção) e cria cópia em Manutenção.
    - Demais ações de desligamento -> marca linha como VAGO.
    """
    if not enabled:
        return True, "Integração com telefonia desabilitada."

    def _is_postgres_db() -> bool:
        url = str(settings.DATABASE_URL or "")
        return url.startswith("postgresql") or "postgres" in url.lower()

    # Quando usamos o PostgreSQL unificado (mesmo banco do Gerenciamento),
    # ignoramos TELEFONES_DB_PATH (legado SQLite) e aplicamos a atualização
    # diretamente na tabela `linhas` do PostgreSQL.
    if _is_postgres_db():
        return _sync_offboarding_to_telefones_postgres(
            employee_name=employee_name,
            asset_tag=asset_tag,
            action=action,
            maintenance_reason=maintenance_reason,
            return_date=return_date,
            ticket_id=ticket_id,
            audit_user_id=audit_user_id,
            audit_username=audit_username,
        )

    if not db_path:
        return False, "TELEFONES_DB_PATH não configurado."

    db_file = Path(db_path)
    if not db_file.exists():
        return False, f"Banco de telefonia não encontrado: {db_file}"

    if not employee_name.strip():
        return False, "Nome do colaborador não informado para integração."

    known_actions = {a.value for a in OffboardingAction}
    if action not in known_actions:
        return False, f"Ação inválida para integração: {action}."

    conn = sqlite3.connect(str(db_file), timeout=15)
    conn.row_factory = sqlite3.Row
    try:
        schema_error = _validate_required_schema(conn)
        if schema_error:
            return False, schema_error

        rows = _find_rows(conn, employee_name, asset_tag)
        if not rows:
            return False, f"Nenhuma linha ativa encontrada para '{employee_name}'."

        for row in rows:
            _sync_team_leadership_if_needed(conn, row, employee_name.strip())
            if action in MAINTENANCE_ACTIONS:
                _create_maintenance_copy(
                    conn,
                    row,
                    employee_name.strip(),
                    asset_tag,
                    maintenance_reason.strip(),
                    return_date.strip(),
                    ticket_id,
                )
                _apply_maintenance_original(
                    conn,
                    row,
                    employee_name.strip(),
                    maintenance_reason.strip(),
                    return_date.strip(),
                    ticket_id,
                )
            else:
                _apply_vacancy(conn, row, employee_name.strip())

        conn.commit()
        mode = "manutenção" if action in MAINTENANCE_ACTIONS else "vaga"
        return True, f"Integração telefonia OK. {len(rows)} linha(s) atualizada(s) para {mode}."
    except Exception as exc:
        conn.rollback()
        logger.exception("Falha na integração telefonia")
        return False, f"Falha na integração telefonia [{exc.__class__.__name__}]: {exc}"
    finally:
        conn.close()


def _find_rows_postgres(*, employee_name: str, asset_tag: str) -> list[dict]:
    """
    Busca linhas ativas no PostgreSQL.
    Prioriza identificação por ativo/linha/codigo (mais confiável).
    """
    name = (employee_name or "").strip()
    tag = (asset_tag or "").strip()
    if not name:
        return []

    exclude_names = ("vago", "manutenção", "manutencao")

    with engine.connect() as conn:
        if tag:
            by_tag = conn.execute(
                text(
                    """
                    SELECT
                        id, nome, nome_usuario_snapshot, patrimonio, codigo, codigo_usuario_snapshot,
                        aparelho, modelo, linha, modo,
                        equipe, equipe_padrao, segmento, papel, gestor, supervisor, observacao
                    FROM linhas
                    WHERE modo = 'ativas'
                      AND (patrimonio = :tag OR codigo = :tag OR linha = :tag)
                      AND lower(trim(coalesce(segmento, ''))) NOT LIKE 'manuten%'
                      AND lower(trim(coalesce(equipe_padrao, ''))) NOT LIKE 'manuten%'
                      AND lower(trim(coalesce(nome, nome_usuario_snapshot))) NOT IN ('vago', 'manutenção', 'manutencao')
                    """
                ),
                {"tag": tag},
            ).mappings().all()
            if by_tag:
                return [dict(r) for r in by_tag]

        # Match direto por nome (aceita tanto `nome` quanto snapshot `nome_usuario_snapshot`)
        by_name = conn.execute(
            text(
                """
                SELECT
                    id, nome, nome_usuario_snapshot, patrimonio, codigo, codigo_usuario_snapshot,
                    aparelho, modelo, linha, modo,
                    equipe, equipe_padrao, segmento, papel, gestor, supervisor, observacao
                FROM linhas
                WHERE modo = 'ativas'
                  AND lower(trim(coalesce(nome, nome_usuario_snapshot))) = lower(trim(:name))
                  AND lower(trim(coalesce(nome, nome_usuario_snapshot))) NOT IN :exclude
                  AND lower(coalesce(segmento, '')) NOT LIKE 'manuten%'
                """
            ),
            {"name": name, "exclude": exclude_names},
        ).mappings().all()
        if by_name:
            return [dict(r) for r in by_name]

        # Fallback acento-insensível: traz candidatos e filtra em Python
        candidates = conn.execute(
            text(
                """
                SELECT
                    id, nome, nome_usuario_snapshot, patrimonio, codigo, codigo_usuario_snapshot,
                    aparelho, modelo, linha, modo,
                    equipe, equipe_padrao, segmento, papel, gestor, supervisor, observacao
                FROM linhas
                WHERE modo = 'ativas'
                  AND nome IS NOT NULL AND trim(nome) <> ''
                  AND lower(coalesce(segmento, '')) NOT LIKE 'manuten%'
                  AND lower(trim(coalesce(nome, nome_usuario_snapshot))) NOT IN :exclude
                ORDER BY id DESC
                LIMIT 500
                """
            ),
            {"exclude": exclude_names},
        ).mappings().all()

        name_key = _normalize_key(name)
        for r in candidates:
            r = dict(r)
            if _normalize_key(r.get("nome") or r.get("nome_usuario_snapshot")) == name_key:
                return [r]

    return []


def _sync_team_leadership_if_needed_postgres(*, row: dict, employee_name: str) -> None:
    team = (row.get("equipe_padrao") or "").strip()
    segment = (row.get("segmento") or "").strip()
    if not team or not segment:
        return

    role = _normalize(row.get("papel") or "")
    with engine.begin() as conn:
        if role == "gerente":
            conn.execute(
                text(
                    """
                    UPDATE linhas
                    SET gestor = 'Vago'
                    WHERE modo = 'ativas'
                      AND equipe_padrao = :team
                      AND segmento = :segment
                      AND lower(trim(coalesce(gestor, ''))) = lower(trim(:employee_name))
                    """
                ),
                {"team": team, "segment": segment, "employee_name": employee_name},
            )
        if role == "supervisor":
            conn.execute(
                text(
                    """
                    UPDATE linhas
                    SET supervisor = 'Vago'
                    WHERE modo = 'ativas'
                      AND equipe_padrao = :team
                      AND segmento = :segment
                      AND lower(trim(coalesce(supervisor, ''))) = lower(trim(:employee_name))
                    """
                ),
                {"team": team, "segment": segment, "employee_name": employee_name},
            )


def _apply_vacancy_postgres(
    *,
    row: dict,
    employee_name: str,
    ticket_id: int | None = None,
    audit_user_id: Optional[int] = None,
    audit_username: Optional[str] = None,
) -> None:
    note = f"Linha marcada como VAGO automaticamente via desligamento ({employee_name})"
    if ticket_id is not None:
        note = f"{note} [ticket_id={ticket_id}]"

    linha_id = int(row["id"])
    antes = fetch_linha_snapshot(linha_id)
    new_obs = _append_note(row.get("observacao"), note)
    with engine.begin() as conn:
        conn.execute(
            text(
                """
                UPDATE linhas
                SET
                    nome = 'VAGO',
                    nome_guerra = 'VAGO',
                    codigo = 'VAGO',
                    nome_usuario_snapshot = 'VAGO',
                    codigo_usuario_snapshot = 'VAGO',
                    gestor = '',
                    supervisor = '',
                    observacao = :obs
                WHERE id = :id
                """
            ),
            {"obs": new_obs, "id": linha_id},
        )
    audit_linha_update(
        acao="desligamento_linha",
        linha_id=linha_id,
        antes=antes,
        ticket_id=ticket_id,
        detalhes=note,
        user_id=audit_user_id,
        username=audit_username or "",
    )


def _get_maintenance_labels_postgres() -> tuple[str, str, str]:
    # IMPORTANTE:
    # Sua UI filtra por exatamente "Manutenção" (com acento).
    # Para evitar qualquer problema de encoding na própria fonte,
    # forçamos o valor usando escapes unicode.
    mnt = "Manuten\u00e7\u00e3o"  # Manutenção
    return mnt, mnt, mnt


def _build_mnt_line_identifier(*, source_line: str, row_id: int | None, ticket_id: int | None) -> str:
    """
    Gera um identificador curto (até 30 chars) para `numero_linha`/`linha` em cópia de manutenção.
    """
    sline = (source_line or "").strip()
    suffix = str(ticket_id or row_id or "").strip()
    base = f"MNT-{suffix}-{sline}"
    # `numero_linha` no schema é VARCHAR(30): garanta limite evitando colidir com truncamento aleatório.
    if len(base) <= 30:
        return base
    # fallback: usa o fim do source_line
    tail = sline[-12:] if sline else ""
    base2 = f"MNT-{suffix}-{tail}"
    return base2[:30]


def _create_maintenance_copy_postgres(
    *,
    row: dict,
    employee_name: str,
    asset_tag: str,
    reason: str,
    return_date: str,
    ticket_id: int | None = None,
    audit_user_id: Optional[int] = None,
    audit_username: Optional[str] = None,
) -> None:
    maintenance_segment, maintenance_group, maintenance_team = _get_maintenance_labels_postgres()

    source_line = str(row.get("linha") or "").strip()
    mnt_line = _build_mnt_line_identifier(
        source_line=source_line,
        row_id=row.get("id"),
        ticket_id=ticket_id,
    )

    # Datas do Gerenciamento:
    # - `Data da Troca` deve refletir a data do chamado (hoje), para ficar em ordem recente->antiga.
    # - `Data Retorno` deve refletir a data de devolução do ticket.
    now = datetime.now()
    call_date = now.strftime("%Y-%m-%d")
    event_date = (return_date or "").strip() or call_date
    data_troca = call_date
    data_retorno = (return_date or "").strip() or ""

    ticket_suffix = f" [ticket_id={ticket_id}]" if ticket_id else ""
    note = (
        f"Cópia criada para manutenção via desligamento ({employee_name}){ticket_suffix}. "
        f"Data: {event_date}"
    )
    if reason:
        note = f"{note}. Motivo: {reason}"

    new_obs = _append_note(row.get("observacao"), note)

    patrimonio = (asset_tag or "").strip() or row.get("patrimonio")
    codigo_val = (asset_tag or "").strip() or row.get("codigo")

    with engine.begin() as conn:
        conn.execute(
            text(
                """
                INSERT INTO linhas (
                    numero_linha, linha,
                    modo, modo_operacao,
                    nome, nome_guerra,
                    codigo, codigo_usuario_snapshot,
                    nome_usuario_snapshot,
                    patrimonio, aparelho, modelo, imei_a, imei_b, chip, marca,
                    segmento, grupo_equipe, equipe_padrao, equipe,
                    papel, gestor, supervisor,
                    data_troca, data_retorno,
                    data_ocorrencia,
                    observacao
                )
                VALUES (
                    :numero_linha, :linha,
                    'ativas', 'ativas',
                    :nome, :nome_guerra,
                    :codigo, :codigo_usuario_snapshot,
                    :nome_usuario_snapshot,
                    :patrimonio, :aparelho, :modelo, :imei_a, :imei_b, :chip, :marca,
                    :segmento, :grupo_equipe, :equipe_padrao, :equipe,
                    :papel, :gestor, :supervisor,
                    :data_troca, :data_retorno,
                    :data_ocorrencia,
                    :observacao
                )
                ON CONFLICT (numero_linha) DO NOTHING
                """
            ),
            {
                "numero_linha": mnt_line,
                "linha": mnt_line,
                "nome": row.get("nome"),
                "nome_guerra": row.get("nome"),
                "codigo": codigo_val,
                "codigo_usuario_snapshot": row.get("codigo_usuario_snapshot") or codigo_val,
                "nome_usuario_snapshot": row.get("nome_usuario_snapshot") or row.get("nome"),
                "patrimonio": patrimonio,
                "aparelho": row.get("aparelho"),
                "modelo": row.get("modelo"),
                "imei_a": row.get("imei_a"),
                "imei_b": row.get("imei_b"),
                "chip": row.get("chip"),
                "marca": row.get("marca"),
                "segmento": maintenance_segment,
                "grupo_equipe": maintenance_group,
                "equipe_padrao": maintenance_team,
                "equipe": maintenance_team,
                "papel": row.get("papel"),
                "gestor": row.get("gestor"),
                "supervisor": row.get("supervisor"),
                "data_troca": data_troca,
                "data_retorno": data_retorno,
                "data_ocorrencia": data_troca,
                "observacao": new_obs,
            },
        )
    new_row = fetch_linha_snapshot_by_numero(mnt_line)
    if new_row.get("id"):
        audit_linha_create(
            linha_id=int(new_row["id"]),
            depois=new_row,
            ticket_id=ticket_id,
            detalhes=note,
            user_id=audit_user_id,
            username=audit_username or "",
            acao="enviar_manutencao",
        )


def fetch_linha_snapshot_by_numero(numero_linha: str) -> dict:
    """Busca linha pelo número (helper local para auditoria pós-insert)."""
    num = (numero_linha or "").strip()
    if not num:
        return {}
    try:
        with engine.connect() as conn:
            row = conn.execute(
                text(
                    """
                    SELECT * FROM linhas
                    WHERE lower(trim(coalesce(numero_linha, ''))) = lower(trim(:nl))
                       OR lower(trim(coalesce(linha, ''))) = lower(trim(:nl))
                    ORDER BY id DESC
                    LIMIT 1
                    """
                ),
                {"nl": num},
            ).mappings().first()
            return dict(row) if row else {}
    except Exception:
        logger.exception("Falha ao buscar linha por numero=%s", num)
        return {}


def _apply_maintenance_only_postgres(
    *,
    row: dict,
    employee_name: str,
    reason: str,
    return_date: str,
    ticket_id: int | None = None,
    audit_user_id: Optional[int] = None,
    audit_username: Optional[str] = None,
) -> None:
    maintenance_segment, _, _ = _get_maintenance_labels_postgres()
    now = datetime.now()
    call_date = now.strftime("%Y-%m-%d")
    event_date = (return_date or "").strip() or call_date
    data_troca = call_date
    data_retorno = (return_date or "").strip() or ""

    ticket_suffix = f" [ticket_id={ticket_id}]" if ticket_id else ""
    note = (
        f"Linha movida para manutenção via desligamento ({employee_name}){ticket_suffix}. "
        f"Data: {event_date}"
    )
    if reason:
        note = f"{note}. Motivo: {reason}"

    linha_id = int(row["id"])
    antes = fetch_linha_snapshot(linha_id)
    new_obs = _append_note(row.get("observacao"), note)

    with engine.begin() as conn:
        conn.execute(
            text(
                """
                UPDATE linhas
                SET
                    segmento = :segmento,
                    modo = 'ativas',
                    modo_operacao = 'ativas',
                    data_troca = :data_troca,
                    data_retorno = :data_retorno,
                    data_ocorrencia = :data_ocorrencia,
                    observacao = :obs
                WHERE id = :id
                """
            ),
            {
                "segmento": maintenance_segment,
                "obs": new_obs,
                "id": linha_id,
                "data_troca": data_troca,
                "data_retorno": data_retorno,
                "data_ocorrencia": data_troca,
            },
        )
    audit_linha_update(
        acao="desligamento_linha",
        linha_id=linha_id,
        antes=antes,
        ticket_id=ticket_id,
        detalhes=note,
        user_id=audit_user_id,
        username=audit_username or "",
    )


def _sync_offboarding_to_telefones_postgres(
    *,
    employee_name: str,
    asset_tag: str,
    action: str,
    maintenance_reason: str = "",
    return_date: str = "",
    ticket_id: int | None = None,
    audit_user_id: Optional[int] = None,
    audit_username: Optional[str] = None,
) -> Tuple[bool, str]:
    """
    Integração PostgreSQL unificada (linhas do Gerenciamento).

    Regras pedidas:
    - `offboarding_with_maintenance`: cria cópia no segmento `Manutenção` e
      marca a linha original como `VAGO` no segmento/equipe original.
    - `maintenance_only`: move a linha para segmento `Manutenção` (sem marcar como VAGO).
    - `without_charger`: marca linha como VAGO (chamado permanece em aberto pelo status).
    - `not_delivered`: marca como VAGO (mas a gente chama apenas quando o chamado for fechado, conforme regra do seu fluxo).
    """
    if not (employee_name or "").strip():
        return False, "Nome do colaborador não informado para integração."

    known_actions = {a.value for a in OffboardingAction}
    if action not in known_actions:
        return False, f"Ação inválida para integração: {action}."

    rows = _find_rows_postgres(employee_name=employee_name, asset_tag=asset_tag)
    if not rows:
        return False, f"Nenhuma linha ativa encontrada para '{employee_name}'."

    for row in rows:
        row = dict(row)
        if action != OffboardingAction.MAINTENANCE_ONLY.value:
            _sync_team_leadership_if_needed_postgres(row=row, employee_name=employee_name.strip())

        if action == OffboardingAction.OFFBOARDING_WITH_MAINTENANCE.value:
            _create_maintenance_copy_postgres(
                row=row,
                employee_name=employee_name.strip(),
                asset_tag=asset_tag,
                reason=maintenance_reason.strip(),
                return_date=return_date.strip(),
                ticket_id=ticket_id,
                audit_user_id=audit_user_id,
                audit_username=audit_username,
            )
            _apply_vacancy_postgres(
                row=row,
                employee_name=employee_name.strip(),
                ticket_id=ticket_id,
                audit_user_id=audit_user_id,
                audit_username=audit_username,
            )
        elif action == OffboardingAction.MAINTENANCE_ONLY.value:
            _apply_maintenance_only_postgres(
                row=row,
                employee_name=employee_name.strip(),
                reason=maintenance_reason.strip(),
                return_date=return_date.strip(),
                ticket_id=ticket_id,
                audit_user_id=audit_user_id,
                audit_username=audit_username,
            )
        else:
            _apply_vacancy_postgres(
                row=row,
                employee_name=employee_name.strip(),
                ticket_id=ticket_id,
                audit_user_id=audit_user_id,
                audit_username=audit_username,
            )

    if action == OffboardingAction.MAINTENANCE_ONLY.value:
        mode = "manutenção"
    elif action == OffboardingAction.OFFBOARDING_WITH_MAINTENANCE.value:
        mode = "manutenção + vaga"
    else:
        mode = "vaga"
    return True, f"Integração telefonia OK. {len(rows)} linha(s) atualizada(s) para {mode}."


def get_offboarding_prefill(
    *,
    db_path: str,
    employee_name: str,
) -> Tuple[bool, str, Optional[dict]]:
    """
    Busca dados da linha ativa para pré-preencher formulário de desligamento.
    """
    def _is_postgres_db() -> bool:
        url = str(settings.DATABASE_URL or "")
        return url.startswith("postgresql") or "postgres" in url.lower()

    if _is_postgres_db():
        return _get_offboarding_prefill_postgres(employee_name=employee_name)

    if not db_path:
        return False, "TELEFONES_DB_PATH não configurado.", None

    name = (employee_name or "").strip()
    if not name:
        return False, "Nome do colaborador não informado.", None

    db_file = Path(db_path)
    if not db_file.exists():
        return False, f"Banco de telefonia não encontrado: {db_file}", None

    conn = sqlite3.connect(str(db_file), timeout=15)
    conn.row_factory = sqlite3.Row
    try:
        schema_error = _validate_required_schema(conn)
        if schema_error:
            return False, schema_error, None

        # Prioriza linha operacional do colaborador (evita registros de manutenção/vago).
        row = conn.execute(
            """
            SELECT id, nome, equipe_padrao, equipe, patrimonio, codigo, aparelho, modelo, linha, modo
            FROM linhas
            WHERE modo = 'ativas'
              AND lower(trim(nome)) = lower(trim(?))
              AND lower(trim(nome)) NOT IN ('vago', 'manutenção', 'manutencao')
              AND lower(coalesce(segmento, '')) NOT LIKE 'manuten%'
            ORDER BY id DESC
            LIMIT 1
            """,
            (name,),
        ).fetchone()
        if not row:
            # Fallback acento-insensível para nomes com variação.
            rows = conn.execute(
                """
                SELECT id, nome, equipe_padrao, equipe, patrimonio, codigo, aparelho, modelo, linha, modo
                FROM linhas
                WHERE modo = 'ativas'
                  AND lower(trim(nome)) NOT IN ('vago', 'manutenção', 'manutencao')
                  AND lower(coalesce(segmento, '')) NOT LIKE 'manuten%'
                ORDER BY id DESC
                """,
            ).fetchall()
            name_key = _normalize_key(name)
            row = next((r for r in rows if _normalize_key(r["nome"]) == name_key), None)

        if not row:
            return False, f"Nenhuma linha ativa encontrada para '{name}'.", None

        data = {
            "employee_name": row["nome"] or name,
            "user_department": (row["equipe_padrao"] or row["equipe"] or "").strip() or None,
            "asset_tag": (row["patrimonio"] or row["codigo"] or "").strip() or None,
            "device_model": (row["modelo"] or row["aparelho"] or "").strip() or None,
            "line": (row["linha"] or "").strip() or None,
            "source_id": row["id"],
        }
        return True, "Pré-preenchimento carregado.", data
    except Exception as exc:
        logger.exception("Falha no pré-preenchimento telefonia")
        return False, f"Falha ao carregar pré-preenchimento [{exc.__class__.__name__}]: {exc}", None
    finally:
        conn.close()


def _get_offboarding_prefill_postgres(*, employee_name: str) -> Tuple[bool, str, Optional[dict]]:
    """
    Versão PostgreSQL unificada.
    Procura uma linha ativa no mesmo banco do Gerenciamento (`linhas`).
    """
    name = (employee_name or "").strip()
    if not name:
        return False, "Nome do colaborador não informado.", None

    try:
        sql = text(
            """
            SELECT
                id,
                nome,
                nome_usuario_snapshot,
                equipe_padrao,
                equipe,
                patrimonio,
                codigo,
                codigo_usuario_snapshot,
                aparelho,
                modelo,
                linha,
                modo
            FROM linhas
            WHERE modo = 'ativas'
              AND lower(trim(coalesce(nome, nome_usuario_snapshot))) = lower(trim(:name))
              AND lower(trim(coalesce(nome, nome_usuario_snapshot))) NOT IN ('vago', 'manutenção', 'manutencao')
              AND lower(coalesce(segmento, '')) NOT LIKE 'manuten%'
            ORDER BY
              (CASE
                 WHEN patrimonio IS NOT NULL OR codigo IS NOT NULL OR codigo_usuario_snapshot IS NOT NULL THEN 1
                 ELSE 0
               END) DESC,
              id DESC
            LIMIT 1
            """
        )
        with engine.connect() as conn:
            row = conn.execute(sql, {"name": name}).mappings().first()

            # Fallback com normalização (mesmo comportamento da versão SQLite)
            if not row:
                candidates_sql = text(
                    """
                    SELECT
                        id,
                        nome,
                        nome_usuario_snapshot,
                        equipe_padrao,
                        equipe,
                        patrimonio,
                        codigo,
                        codigo_usuario_snapshot,
                        aparelho,
                        modelo,
                        linha,
                        modo
                    FROM linhas
                    WHERE modo = 'ativas'
                      AND lower(trim(coalesce(nome, nome_usuario_snapshot))) NOT IN ('vago', 'manutenção', 'manutencao')
                      AND lower(coalesce(segmento, '')) NOT LIKE 'manuten%'
                    ORDER BY id DESC
                    LIMIT 500
                    """
                )
                candidates = conn.execute(candidates_sql).mappings().all()
                name_key = _normalize_key(name)
                row = next(
                    (r for r in candidates if _normalize_key(r.get("nome")) == name_key),
                    None,
                )

        if not row:
            return False, f"Nenhuma linha ativa encontrada para '{name}'.", None

        data = {
            "employee_name": row.get("nome") or row.get("nome_usuario_snapshot") or name,
            "user_department": (row.get("equipe_padrao") or row.get("equipe") or "").strip() or None,
            "asset_tag": (row.get("patrimonio") or "").strip() or None,
            "device_model": (row.get("modelo") or row.get("aparelho") or "").strip() or None,
            "line": (row.get("linha") or "").strip() or None,
            "source_id": row.get("id"),
        }
        return True, "Pré-preenchimento carregado.", data

    except Exception as exc:
        logger.exception("Falha no pré-preenchimento telefonia (Postgres)")
        return False, f"Falha ao carregar pré-preenchimento [{exc.__class__.__name__}]: {exc}", None


# ---------------------------------------------------------------------------
# Novas funções: ciclo de vida de linhas (onboarding, manutenção, roubo/perda,
# transferência) — integração direta via PostgreSQL compartilhado.
# ---------------------------------------------------------------------------

def buscar_linha_por_codigo_ou_nome(
    *,
    codigo: str = "",
    nome: str = "",
) -> Optional[dict]:
    """
    Busca uma linha ativa no PostgreSQL.
    Prioridade: codigo (matrícula) > nome.
    Retorna dict com todos os campos de prévia ou None.
    """
    codigo = (codigo or "").strip()
    nome = (nome or "").strip()
    if not codigo and not nome:
        return None

    exclude_names = ("vago", "manutenção", "manutencao")
    select_cols = """
        id, nome, nome_usuario_snapshot, codigo, codigo_usuario_snapshot,
        linha, equipe, equipe_padrao, aparelho, modelo, imei_a, imei_b,
        marca, chip, operadora, numero_serie, ativo, patrimonio,
        cargo, setor, email, gestor, empresa, observacao
    """

    try:
        with engine.connect() as conn:
            # 1) Por código (matrícula)
            if codigo:
                row = conn.execute(
                    text(
                        f"""
                        SELECT {select_cols}
                        FROM linhas
                        WHERE modo = 'ativas'
                          AND (
                              lower(trim(coalesce(codigo, ''))) = lower(trim(:codigo))
                              OR lower(trim(coalesce(codigo_usuario_snapshot, ''))) = lower(trim(:codigo))
                          )
                          AND lower(trim(coalesce(nome, nome_usuario_snapshot, ''))) NOT IN :exclude
                          AND lower(coalesce(segmento, '')) NOT LIKE 'manuten%'
                        ORDER BY id DESC
                        LIMIT 1
                        """
                    ),
                    {"codigo": codigo, "exclude": exclude_names},
                ).mappings().first()
                if row:
                    return dict(row)

            # 2) Por nome (direto)
            if nome:
                row = conn.execute(
                    text(
                        f"""
                        SELECT {select_cols}
                        FROM linhas
                        WHERE modo = 'ativas'
                          AND lower(trim(coalesce(nome, nome_usuario_snapshot, ''))) = lower(trim(:nome))
                          AND lower(trim(coalesce(nome, nome_usuario_snapshot, ''))) NOT IN :exclude
                          AND lower(coalesce(segmento, '')) NOT LIKE 'manuten%'
                        ORDER BY id DESC
                        LIMIT 1
                        """
                    ),
                    {"nome": nome, "exclude": exclude_names},
                ).mappings().first()
                if row:
                    return dict(row)

                # 3) Fallback acento-insensível
                candidates = conn.execute(
                    text(
                        f"""
                        SELECT {select_cols}
                        FROM linhas
                        WHERE modo = 'ativas'
                          AND nome IS NOT NULL AND trim(nome) <> ''
                          AND lower(trim(coalesce(nome, nome_usuario_snapshot, ''))) NOT IN :exclude
                          AND lower(coalesce(segmento, '')) NOT LIKE 'manuten%'
                        ORDER BY id DESC
                        LIMIT 500
                        """
                    ),
                    {"exclude": exclude_names},
                ).mappings().all()
                nome_key = _normalize_key(nome)
                for r in candidates:
                    if _normalize_key(r.get("nome") or r.get("nome_usuario_snapshot") or "") == nome_key:
                        return dict(r)
    except Exception as exc:
        logger.exception("Falha em buscar_linha_por_codigo_ou_nome")
        return None

    return None


def listar_equipes_e_setores() -> dict:
    """
    Retorna listas distintas de equipes, setores, gestores e empresas
    cadastrados na tabela linhas. Usado para popular autocompletes.
    """
    try:
        with engine.connect() as conn:
            def _distinct(col: str) -> list[str]:
                rows = conn.execute(
                    text(
                        f"""
                        SELECT DISTINCT trim({col}) AS val
                        FROM linhas
                        WHERE modo = 'ativas'
                          AND {col} IS NOT NULL
                          AND trim({col}) <> ''
                          AND lower(trim({col})) NOT IN ('vago', 'manutenção', 'manutencao')
                        ORDER BY val
                        """
                    )
                ).fetchall()
                return [r[0] for r in rows if r[0]]

            return {
                "equipes": _distinct("equipe"),
                "setores": _distinct("setor"),
                "gestores": _distinct("gestor"),
                "empresas": _distinct("empresa"),
            }
    except Exception:
        logger.exception("Falha em listar_equipes_e_setores")
        return {"equipes": [], "setores": [], "gestores": [], "empresas": []}


def buscar_linha_por_numero(*, numero: str) -> Optional[dict]:
    """
    Busca uma linha pelo número de telefone — inclui linhas VAGO.
    Usada no fluxo de Novo Usuário para pré-preencher equipe/gestor/setor/empresa.
    """
    numero = (numero or "").strip()
    if not numero:
        return None

    select_cols = """
        id, nome, nome_usuario_snapshot, codigo, codigo_usuario_snapshot,
        linha, equipe, equipe_padrao, aparelho, modelo, imei_a, imei_b,
        marca, chip, operadora, numero_serie, ativo, patrimonio,
        cargo, setor, email, gestor, empresa, observacao
    """

    try:
        with engine.connect() as conn:
            row = conn.execute(
                text(
                    f"""
                    SELECT {select_cols}
                    FROM linhas
                    WHERE modo = 'ativas'
                      AND (
                          lower(trim(coalesce(linha, ''))) = lower(trim(:numero))
                          OR lower(trim(coalesce(numero_linha, ''))) = lower(trim(:numero))
                      )
                    ORDER BY id DESC
                    LIMIT 1
                    """
                ),
                {"numero": numero},
            ).mappings().first()
            if row:
                return dict(row)
    except Exception:
        logger.exception("Falha em buscar_linha_por_numero")

    return None


def criar_nova_linha(
    *,
    numero_linha: str,
    nome: str,
    codigo: str = "",
    equipe: str = "",
    setor: str = "",
    gestor: str = "",
    empresa: str = "",
    cargo: str = "",
    email: str = "",
    nome_guerra: str = "",
    imei_a: str = "",
    imei_b: str = "",
    marca: str = "",
    modelo: str = "",
    aparelho: str = "",
    numero_serie: str = "",
    ativo: str = "",
    chip: str = "",
    operadora: str = "",
    ticket_id: Optional[int] = None,
    audit_user_id: Optional[int] = None,
    audit_username: Optional[str] = None,
) -> Tuple[bool, str]:
    """
    Cria uma nova linha no banco de telefones com todos os dados do colaborador.
    Retorna (True, mensagem) ou (False, motivo_erro).
    """
    numero_linha = (numero_linha or "").strip()
    nome = (nome or "").strip()

    if not numero_linha:
        return False, "Número da linha é obrigatório."
    if not nome:
        return False, "Nome do colaborador é obrigatório."

    ticket_suffix = f" [ticket_id={ticket_id}]" if ticket_id else ""
    note = f"Linha criada via Sistema de Chamados — {nome}{ticket_suffix}."

    try:
        with engine.connect() as check_conn:
            exists = check_conn.execute(
                text(
                    """
                    SELECT id FROM linhas
                    WHERE lower(trim(coalesce(linha, ''))) = lower(trim(:nl))
                       OR lower(trim(coalesce(numero_linha, ''))) = lower(trim(:nl))
                    LIMIT 1
                    """
                ),
                {"nl": numero_linha},
            ).first()
            if exists:
                return False, f"Já existe uma linha com o número '{numero_linha}' no banco."

        with engine.begin() as conn:
            result = conn.execute(
                text(
                    """
                    INSERT INTO linhas (
                        numero_linha, linha, modo, modo_operacao,
                        nome, nome_usuario_snapshot, nome_guerra,
                        codigo, codigo_usuario_snapshot,
                        equipe, equipe_padrao,
                        setor, gestor, empresa, cargo, email,
                        imei_a, imei_b, marca, modelo, aparelho,
                        numero_serie, ativo, chip, operadora,
                        observacao
                    ) VALUES (
                        :numero_linha, :linha, 'ativas', 'ativas',
                        :nome, :nome, :nome_guerra,
                        :codigo, :codigo,
                        :equipe, :equipe,
                        :setor, :gestor, :empresa, :cargo, :email,
                        :imei_a, :imei_b, :marca, :modelo, :aparelho,
                        :numero_serie, :ativo, :chip, :operadora,
                        :observacao
                    )
                    RETURNING id
                    """
                ),
                {
                    "numero_linha": numero_linha,
                    "linha": numero_linha,
                    "nome": nome,
                    "nome_guerra": nome_guerra or None,
                    "codigo": codigo or None,
                    "equipe": equipe or None,
                    "setor": setor or None,
                    "gestor": gestor or None,
                    "empresa": empresa or None,
                    "cargo": cargo or None,
                    "email": email or None,
                    "imei_a": imei_a or None,
                    "imei_b": imei_b or None,
                    "marca": marca or None,
                    "modelo": modelo or None,
                    "aparelho": aparelho or None,
                    "numero_serie": numero_serie or None,
                    "ativo": ativo or None,
                    "chip": chip or None,
                    "operadora": operadora or None,
                    "observacao": note,
                },
            )
            new_id = int(result.scalar_one())
        depois = fetch_linha_snapshot(new_id)
        audit_linha_create(
            linha_id=new_id,
            depois=depois,
            ticket_id=ticket_id,
            detalhes=note,
            user_id=audit_user_id,
            username=audit_username or "",
            acao="criar_linha",
        )
        return True, f"Linha {numero_linha} criada com sucesso para {nome}."
    except Exception as exc:
        logger.exception("Falha em criar_nova_linha")
        return False, f"Erro ao criar linha [{exc.__class__.__name__}]: {exc}"


def atribuir_linha(
    *,
    numero_linha: str,
    nome: str,
    codigo: str = "",
    cargo: str = "",
    setor: str = "",
    empresa: str = "",
    equipe: str = "",
    gestor: str = "",
    email: str = "",
    nome_guerra: str = "",
    ticket_id: Optional[int] = None,
    audit_user_id: Optional[int] = None,
    audit_username: Optional[str] = None,
) -> Tuple[bool, str]:
    """
    Onboarding: atribui colaborador a uma linha (preferencialmente VAGO).
    Atualiza campos pessoais. Preserva dados do aparelho.
    """
    numero_linha = (numero_linha or "").strip()
    nome = (nome or "").strip()
    if not numero_linha or not nome:
        return False, "Número da linha e nome do colaborador são obrigatórios."

    ticket_suffix = f" [ticket_id={ticket_id}]" if ticket_id else ""
    note = f"Linha atribuída via onboarding a {nome}{ticket_suffix}."

    try:
        with engine.connect() as read_conn:
            row = read_conn.execute(
                text(
                    """
                    SELECT id, observacao
                    FROM linhas
                    WHERE modo = 'ativas'
                      AND (
                          lower(trim(coalesce(numero_linha, ''))) = lower(trim(:nl))
                          OR lower(trim(coalesce(linha, ''))) = lower(trim(:nl))
                      )
                    ORDER BY id DESC
                    LIMIT 1
                    """
                ),
                {"nl": numero_linha},
            ).mappings().first()

        if not row:
            return False, f"Linha '{numero_linha}' não encontrada no banco de telefones."

        linha_id = int(row["id"])
        antes = fetch_linha_snapshot(linha_id)
        new_obs = _append_note(row.get("observacao"), note)

        with engine.begin() as conn:
            conn.execute(
                text(
                    """
                    UPDATE linhas
                    SET
                        nome = :nome,
                        nome_usuario_snapshot = :nome,
                        nome_guerra = :nome_guerra,
                        codigo = :codigo,
                        codigo_usuario_snapshot = :codigo,
                        cargo = :cargo,
                        setor = :setor,
                        empresa = CASE WHEN :empresa <> '' THEN :empresa ELSE empresa END,
                        equipe = CASE WHEN :equipe <> '' THEN :equipe ELSE equipe END,
                        equipe_padrao = CASE WHEN :equipe <> '' THEN :equipe ELSE equipe_padrao END,
                        gestor = CASE WHEN :gestor <> '' THEN :gestor ELSE gestor END,
                        email = :email,
                        observacao = :obs
                    WHERE id = :id
                    """
                ),
                {
                    "nome": nome,
                    "nome_guerra": nome_guerra or nome,
                    "codigo": codigo or "",
                    "cargo": cargo or "",
                    "setor": setor or "",
                    "empresa": empresa or "",
                    "equipe": equipe or "",
                    "gestor": gestor or "",
                    "email": email or "",
                    "obs": new_obs,
                    "id": linha_id,
                },
            )
        audit_linha_update(
            acao="onboarding_linha",
            linha_id=linha_id,
            antes=antes,
            ticket_id=ticket_id,
            detalhes=note,
            user_id=audit_user_id,
            username=audit_username or "",
        )
        return True, f"Linha '{numero_linha}' atribuída a '{nome}' com sucesso."
    except Exception as exc:
        logger.exception("Falha no onboarding de linha")
        return False, f"Falha ao atribuir linha [{exc.__class__.__name__}]: {exc}"


def atualizar_aparelho(
    *,
    linha_id: int,
    imei_a: str = "",
    imei_b: str = "",
    marca: str = "",
    modelo: str = "",
    aparelho: str = "",
    numero_serie: str = "",
    ativo: str = "",
    chip: str = "",
    observacao_extra: str = "",
    ticket_id: Optional[int] = None,
    audit_user_id: Optional[int] = None,
    audit_username: Optional[str] = None,
) -> Tuple[bool, str]:
    """
    Manutenção/Troca: atualiza apenas os campos do aparelho.
    Preserva todos os campos do colaborador e da linha.
    """
    ticket_suffix = f" [ticket_id={ticket_id}]" if ticket_id else ""
    note = f"Aparelho atualizado (manutenção/troca){ticket_suffix}."
    if observacao_extra:
        note = f"{note} {observacao_extra}"

    try:
        with engine.connect() as read_conn:
            row = read_conn.execute(
                text("SELECT id, observacao FROM linhas WHERE id = :id"),
                {"id": linha_id},
            ).mappings().first()

        if not row:
            return False, f"Linha id={linha_id} não encontrada."

        antes = fetch_linha_snapshot(linha_id)
        new_obs = _append_note(row.get("observacao"), note)

        updates: dict = {"obs": new_obs, "id": linha_id}
        set_parts = ["observacao = :obs"]

        field_map = {
            "imei_a": imei_a,
            "imei_b": imei_b,
            "marca": marca,
            "modelo": modelo,
            "aparelho": aparelho,
            "numero_serie": numero_serie,
            "ativo": ativo,
            "chip": chip,
        }
        for col, val in field_map.items():
            if (val or "").strip():
                set_parts.append(f"{col} = :{col}")
                updates[col] = val.strip()

        with engine.begin() as conn:
            conn.execute(
                text(f"UPDATE linhas SET {', '.join(set_parts)} WHERE id = :id"),
                updates,
            )
        audit_linha_update(
            acao="manutencao_aparelho",
            linha_id=linha_id,
            antes=antes,
            ticket_id=ticket_id,
            detalhes=note,
            user_id=audit_user_id,
            username=audit_username or "",
        )
        return True, "Dados do aparelho atualizados com sucesso."
    except Exception as exc:
        logger.exception("Falha ao atualizar aparelho")
        return False, f"Falha ao atualizar aparelho [{exc.__class__.__name__}]: {exc}"


def registrar_roubo_perda(
    *,
    linha_id: int,
    imei_a: str = "",
    imei_b: str = "",
    marca: str = "",
    modelo: str = "",
    aparelho: str = "",
    numero_serie: str = "",
    ativo: str = "",
    chip: str = "",
    nova_linha: str = "",
    observacao_extra: str = "",
    ticket_id: Optional[int] = None,
    audit_user_id: Optional[int] = None,
    audit_username: Optional[str] = None,
) -> Tuple[bool, str]:
    """
    Roubo/Perda:
    - Cenário A: mesma linha, novo aparelho → atualiza só campos do aparelho
    - Cenário B: nova linha + novo aparelho → atualiza aparelho + campo linha/numero_linha
    """
    nova_linha = (nova_linha or "").strip()
    cenario = "B" if nova_linha else "A"
    ticket_suffix = f" [ticket_id={ticket_id}]" if ticket_id else ""
    note = f"Roubo/Perda — cenário {cenario}{ticket_suffix}."
    if observacao_extra:
        note = f"{note} {observacao_extra}"

    try:
        with engine.connect() as read_conn:
            row = read_conn.execute(
                text("SELECT id, observacao FROM linhas WHERE id = :id"),
                {"id": linha_id},
            ).mappings().first()

        if not row:
            return False, f"Linha id={linha_id} não encontrada."

        antes = fetch_linha_snapshot(linha_id)
        new_obs = _append_note(row.get("observacao"), note)

        updates: dict = {"obs": new_obs, "id": linha_id}
        set_parts = ["observacao = :obs"]

        field_map = {
            "imei_a": imei_a,
            "imei_b": imei_b,
            "marca": marca,
            "modelo": modelo,
            "aparelho": aparelho,
            "numero_serie": numero_serie,
            "ativo": ativo,
            "chip": chip,
        }
        for col, val in field_map.items():
            if (val or "").strip():
                set_parts.append(f"{col} = :{col}")
                updates[col] = val.strip()

        if nova_linha:
            set_parts.append("linha = :nova_linha")
            set_parts.append("numero_linha = :nova_linha")
            updates["nova_linha"] = nova_linha

        with engine.begin() as conn:
            conn.execute(
                text(f"UPDATE linhas SET {', '.join(set_parts)} WHERE id = :id"),
                updates,
            )
        audit_linha_update(
            acao="roubo_perda_linha",
            linha_id=linha_id,
            antes=antes,
            ticket_id=ticket_id,
            detalhes=note,
            user_id=audit_user_id,
            username=audit_username or "",
        )
        msg = (
            f"Roubo/Perda cenário {cenario} registrado. "
            + (f"Nova linha: {nova_linha}." if nova_linha else "Linha mantida.")
        )
        return True, msg
    except Exception as exc:
        logger.exception("Falha ao registrar roubo/perda")
        return False, f"Falha ao registrar roubo/perda [{exc.__class__.__name__}]: {exc}"


def transferir_colaborador(
    *,
    linha_id: int,
    equipe: str,
    setor: str,
    gestor: str,
    cargo: str = "",
    empresa: str = "",
    observacao_extra: str = "",
    ticket_id: Optional[int] = None,
    audit_user_id: Optional[int] = None,
    audit_username: Optional[str] = None,
) -> Tuple[bool, str]:
    """
    Transferência: atualiza equipe, setor, gestor e opcionalmente cargo/empresa.
    Preserva todos os dados do colaborador e do aparelho.
    """
    ticket_suffix = f" [ticket_id={ticket_id}]" if ticket_id else ""
    note = f"Transferência de equipe para '{equipe}'{ticket_suffix}."
    if observacao_extra:
        note = f"{note} {observacao_extra}"

    try:
        with engine.connect() as read_conn:
            row = read_conn.execute(
                text("SELECT id, observacao FROM linhas WHERE id = :id"),
                {"id": linha_id},
            ).mappings().first()

        if not row:
            return False, f"Linha id={linha_id} não encontrada."

        antes = fetch_linha_snapshot(linha_id)
        new_obs = _append_note(row.get("observacao"), note)

        updates: dict = {
            "equipe": equipe,
            "setor": setor,
            "gestor": gestor,
            "obs": new_obs,
            "id": linha_id,
        }
        set_parts = [
            "equipe = :equipe",
            "equipe_padrao = :equipe",
            "setor = :setor",
            "gestor = :gestor",
            "observacao = :obs",
        ]

        if (cargo or "").strip():
            set_parts.append("cargo = :cargo")
            updates["cargo"] = cargo.strip()

        if (empresa or "").strip():
            set_parts.append("empresa = :empresa")
            updates["empresa"] = empresa.strip()

        with engine.begin() as conn:
            conn.execute(
                text(f"UPDATE linhas SET {', '.join(set_parts)} WHERE id = :id"),
                updates,
            )
        audit_linha_update(
            acao="transferencia_equipe",
            linha_id=linha_id,
            antes=antes,
            ticket_id=ticket_id,
            detalhes=note,
            user_id=audit_user_id,
            username=audit_username or "",
        )
        return True, f"Colaborador transferido para equipe '{equipe}' com sucesso."
    except Exception as exc:
        logger.exception("Falha na transferência")
        return False, f"Falha na transferência [{exc.__class__.__name__}]: {exc}"

