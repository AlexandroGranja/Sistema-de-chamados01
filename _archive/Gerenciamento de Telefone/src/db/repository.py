"""Repositório para acesso ao banco de dados."""

import json
import sqlite3
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Optional

import pandas as pd

from src.core.config import get_database_backend, get_database_url, get_db_path

try:
    import psycopg
    from psycopg.errors import UniqueViolation
    from psycopg.errors import DeadlockDetected
except ImportError:  # pragma: no cover - ambiente sem psycopg
    psycopg = None
    UniqueViolation = Exception
    DeadlockDetected = Exception


LEGACY_COL_MAP = {
    "↕ Ordem": "ordem_manual",
    "Codigo": "codigo",
    "Nome": "nome",
    "Equipe": "equipe",
    "EquipePadrao": "equipe_padrao",
    "GrupoEquipe": "grupo_equipe",
    "TipoEquipe": "tipo_equipe",
    "Localidade": "localidade",
    "Data da Troca": "data_troca",
    "Data Retorno": "data_retorno",
    "Data Ocorrência": "data_ocorrencia",
    "Data Solicitação TBS": "data_solicitacao_tbs",
    "Gestor": "gestor",
    "Supervisor": "supervisor",
    "Segmento": "segmento",
    "Papel": "papel",
    "Linha": "linha",
    "E-mail": "email",
    "Gerenciamento": "gerenciamento",
    "IMEI A": "imei_a",
    "IMEI B": "imei_b",
    "CHIP": "chip",
    "Marca": "marca",
    "Aparelho": "aparelho",
    "Modelo": "modelo",
    "Setor": "setor",
    "Cargo": "cargo",
    "Desconto": "desconto",
    "Perfil": "perfil",
    "Empresa": "empresa",
    "Ativo": "ativo",
    "Numero de Serie": "numero_serie",
    "Patrimonio": "patrimonio",
    "Operadora": "operadora",
    "Nome de Guerra": "nome_guerra",
    "Motivo": "motivo",
    "Observação": "observacao",
    "Aba": "aba",
}

REV_COL_MAP = {v: k for k, v in LEGACY_COL_MAP.items()}




def _backend() -> str:
    return get_database_backend()


def _is_postgres() -> bool:
    return _backend() == "postgres"


def _normalize_record_value(value: Any) -> Any:
    if value is None:
        return None
    if isinstance(value, float) and pd.isna(value):
        return None
    text = str(value).strip() if not isinstance(value, (dict, list, bool, int)) else value
    if isinstance(text, str) and not text:
        return None
    return text


def _connect_postgres():
    if psycopg is None:
        raise RuntimeError("psycopg nao esta instalado para uso com PostgreSQL.")
    db_url = get_database_url()
    if not db_url:
        raise RuntimeError("DATABASE_URL nao configurado.")
    return psycopg.connect(db_url)


def get_connection(db_path: Optional[Path] = None):
    """Retorna conexão do backend ativo."""
    if _is_postgres():
        return _connect_postgres()
    path = db_path or get_db_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(path))
    conn.row_factory = sqlite3.Row
    return conn


def criar_usuario(username: str, is_admin: bool = False, email: str = "", db_path: Optional[Path] = None) -> bool:
    """Cria registro local do usuário (sem senha — auth via Keycloak)."""
    conn = get_connection(db_path)
    try:
        if _is_postgres():
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO usuarios_app (username, email, is_admin, auth_provider, ativo)
                    VALUES (%s, %s, %s, 'keycloak', TRUE)
                    """,
                    (username.strip().lower(), email, bool(is_admin)),
                )
            conn.commit()
            return True
        conn.execute(
            "INSERT INTO usuarios (username, is_admin) VALUES (?, ?)",
            (username.strip().lower(), 1 if is_admin else 0),
        )
        conn.commit()
        return True
    except (sqlite3.IntegrityError, UniqueViolation):
        return False
    finally:
        conn.close()


def listar_usuarios(db_path: Optional[Path] = None) -> list[dict]:
    """Lista todos os usuários (sem senha)."""
    conn = get_connection(db_path)
    try:
        if _is_postgres():
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT id, username, is_admin, criado_em FROM usuarios_app ORDER BY username"
                )
                rows = cur.fetchall()
        else:
            rows = conn.execute(
                "SELECT id, username, is_admin, criado_em FROM usuarios ORDER BY username"
            ).fetchall()
        return [
            {"id": r[0], "username": r[1], "is_admin": bool(r[2]), "criado_em": r[3]}
            for r in rows
        ]
    finally:
        conn.close()


def excluir_usuario(username: str, db_path: Optional[Path] = None) -> bool:
    """Exclui usuário. Retorna True se excluiu."""
    conn = get_connection(db_path)
    try:
        if _is_postgres():
            with conn.cursor() as cur:
                cur.execute("DELETE FROM usuarios_app WHERE username = %s", (username.strip().lower(),))
                deleted = cur.rowcount > 0
        else:
            cur = conn.execute("DELETE FROM usuarios WHERE username = ?", (username.strip().lower(),))
            deleted = cur.rowcount > 0
        conn.commit()
        return deleted
    finally:
        conn.close()


def atualizar_senha_usuario(username: str, nova_senha: str, db_path: Optional[Path] = None) -> bool:
    """Senha gerenciada pelo Keycloak — operação não suportada localmente."""
    return False


def tem_usuarios(db_path: Optional[Path] = None) -> bool:
    """Verifica se existe pelo menos um usuário."""
    conn = get_connection(db_path)
    try:
        if _is_postgres():
            with conn.cursor() as cur:
                cur.execute("SELECT COUNT(*) FROM usuarios_app")
                return cur.fetchone()[0] > 0
        return conn.execute("SELECT COUNT(*) FROM usuarios").fetchone()[0] > 0
    finally:
        conn.close()


def obter_usuario_por_username(username: str, db_path: Optional[Path] = None) -> Optional[dict]:
    """Retorna usuário por username (sem senha). Para restaurar sessão."""
    conn = get_connection(db_path)
    try:
        if _is_postgres():
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT username, is_admin FROM usuarios_app WHERE username = %s",
                    (username.strip().lower(),),
                )
                row = cur.fetchone()
        else:
            row = conn.execute(
                "SELECT username, is_admin FROM usuarios WHERE username = ?",
                (username.strip().lower(),),
            ).fetchone()
        if not row:
            return None
        return {"username": row[0], "is_admin": bool(row[1])}
    finally:
        conn.close()






def init_db(db_path: Optional[Path] = None) -> None:
    """Inicializa o schema do banco."""
    schema_name = "schema_postgres.sql" if _is_postgres() else "schema.sql"
    schema_path = Path(__file__).parent / schema_name
    conn = get_connection(db_path)
    try:
        if _is_postgres():
            # Evita deadlocks quando duas instâncias do Streamlit tentam inicializar
            # o schema/alterações ao mesmo tempo.
            lock_key = "gerenciamento_telefones_init_db_v1"
            max_attempts = 3
            for attempt in range(1, max_attempts + 1):
                try:
                    with conn.cursor() as cur:
                        cur.execute("SELECT pg_advisory_lock(hashtext(%s))", (lock_key,))
                        try:
                            cur.execute(schema_path.read_text(encoding="utf-8"))
                            cur.execute("ALTER TABLE linhas ADD COLUMN IF NOT EXISTS ordem_manual INTEGER")
                            # Compatibilidade com a UI do sistema de chamados (React)
                            cur.execute("ALTER TABLE chamados ADD COLUMN IF NOT EXISTS category VARCHAR(100)")
                            cur.execute("ALTER TABLE chamados ADD COLUMN IF NOT EXISTS subcategory VARCHAR(100)")
                            cur.execute("ALTER TABLE chamados ADD COLUMN IF NOT EXISTS location VARCHAR(100)")
                            cur.execute("ALTER TABLE chamados ADD COLUMN IF NOT EXISTS equipment_info TEXT")
                            cur.execute("ALTER TABLE chamados ADD COLUMN IF NOT EXISTS internal_notes TEXT")
                            # Redesign migrations
                            from src.db.migrations import run_migrations
                            run_migrations(cur)
                            conn.commit()
                            return
                        finally:
                            cur.execute("SELECT pg_advisory_unlock(hashtext(%s))", (lock_key,))
                except DeadlockDetected:
                    # Deadlock em migrações raramente acontece mesmo com advisory lock
                    # (ex.: outras migrações externas). Faz retry com backoff simples.
                    if attempt >= max_attempts:
                        raise
                    conn.rollback()
                    sleep_s = 0.6 * attempt
                    time.sleep(sleep_s)

        conn.executescript(schema_path.read_text(encoding="utf-8"))
        cols = {r[1] for r in conn.execute("PRAGMA table_info(linhas)").fetchall()}
        if "data_troca" not in cols:
            conn.execute("ALTER TABLE linhas ADD COLUMN data_troca TEXT")
        if "data_retorno" not in cols:
            conn.execute("ALTER TABLE linhas ADD COLUMN data_retorno TEXT")
        if "data_ocorrencia" not in cols:
            conn.execute("ALTER TABLE linhas ADD COLUMN data_ocorrencia TEXT")
        if "data_solicitacao_tbs" not in cols:
            conn.execute("ALTER TABLE linhas ADD COLUMN data_solicitacao_tbs TEXT")
        if "marca" not in cols:
            conn.execute("ALTER TABLE linhas ADD COLUMN marca TEXT")
        if "patrimonio" not in cols:
            conn.execute("ALTER TABLE linhas ADD COLUMN patrimonio TEXT")
        if "nome_guerra" not in cols:
            conn.execute("ALTER TABLE linhas ADD COLUMN nome_guerra TEXT")
        if "motivo" not in cols:
            conn.execute("ALTER TABLE linhas ADD COLUMN motivo TEXT")
        if "observacao" not in cols:
            conn.execute("ALTER TABLE linhas ADD COLUMN observacao TEXT")
        audit_cols = {r[1] for r in conn.execute("PRAGMA table_info(audit_log)").fetchall()}
        if "chamado_id" not in audit_cols:
            conn.execute("ALTER TABLE audit_log ADD COLUMN chamado_id TEXT")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_audit_chamado_id ON audit_log(chamado_id)")
        conn.commit()
    finally:
        conn.close()


def save_linhas(df: pd.DataFrame, modo: str = "ativas", db_path: Optional[Path] = None) -> int:
    """Salva DataFrame na tabela `linhas`.

    No PostgreSQL, não removemos tudo da tabela para evitar violação de FK com
    `chamados.linha_id` (que referencia `linhas.id`). Em vez disso, fazemos UPSERT
    por `numero_linha` e, quando necessário, deletamos apenas linhas que não
    vieram no DataFrame e que não estejam referenciadas por chamados.
    """
    conn = get_connection(db_path)
    try:
        available = [c for c in LEGACY_COL_MAP if c in df.columns]
        df_export = df[available].copy() if available else pd.DataFrame()
        df_export = df_export.rename(columns=LEGACY_COL_MAP)
        if _is_postgres():
            with conn.cursor() as cur:
                records: list[dict[str, Any]] = []
                if not df_export.empty:
                    for record in df_export.to_dict("records"):
                        rec = {k: _normalize_record_value(v) for k, v in record.items()}
                        # `ordem_manual` precisa ser inteiro no PostgreSQL.
                        if rec.get("ordem_manual") not in (None, ""):
                            try:
                                rec["ordem_manual"] = int(float(str(rec.get("ordem_manual")).strip()))
                            except Exception:
                                rec["ordem_manual"] = None
                        rec["modo"] = modo
                        rec["modo_operacao"] = modo
                        rec["numero_linha"] = rec.get("linha")
                        rec["codigo_usuario_snapshot"] = rec.get("codigo")
                        rec["nome_usuario_snapshot"] = rec.get("nome")
                        rec["email_snapshot"] = rec.get("email")
                        # `numero_linha` é UNIQUE/NOT NULL: se vier vazio, não tenta persistir.
                        if rec.get("numero_linha") in (None, ""):
                            continue
                        records.append(rec)

                if records:
                    insert_cols = sorted({k for rec in records for k in rec.keys()})
                    placeholders = ", ".join(["%s"] * len(insert_cols))
                    columns_sql = ", ".join(insert_cols)

                    # UPSERT por `numero_linha` (evita trocar o `id`, mantendo FK em `chamados`).
                    update_cols = [c for c in insert_cols if c != "numero_linha"]
                    update_set_sql = ", ".join([f"{c} = EXCLUDED.{c}" for c in update_cols])
                    values = [tuple(rec.get(col) for col in insert_cols) for rec in records]

                    cur.executemany(
                        f"""
                        INSERT INTO linhas ({columns_sql})
                        VALUES ({placeholders})
                        ON CONFLICT (numero_linha) DO UPDATE SET {update_set_sql}
                        """.strip(),
                        values,
                    )

                # Deleta apenas o que não veio no DataFrame E não está referenciado por `chamados`.
                # Isso substitui o DELETE "total" anterior, evitando ForeignKeyViolation.
                keys = [r.get("numero_linha") for r in records if r.get("numero_linha") not in (None, "")]
                if keys:
                    placeholders_keys = ", ".join(["%s"] * len(keys))
                    cur.execute(
                        f"""
                        DELETE FROM linhas l
                        WHERE COALESCE(l.modo, l.modo_operacao) = %s
                          AND l.numero_linha NOT IN ({placeholders_keys})
                          AND NOT EXISTS (
                            SELECT 1 FROM chamados c
                            WHERE c.linha_id = l.id
                          )
                        """.strip(),
                        [modo] + keys,
                    )
                else:
                    # Se não há registros para persistir, não deletamos nada que esteja referenciado.
                    cur.execute(
                        """
                        DELETE FROM linhas l
                        WHERE COALESCE(l.modo, l.modo_operacao) = %s
                          AND NOT EXISTS (
                            SELECT 1 FROM chamados c
                            WHERE c.linha_id = l.id
                          )
                        """.strip(),
                        (modo,),
                    )
            conn.commit()
            return len(df_export)

        conn.execute("DELETE FROM linhas WHERE modo = ?", (modo,))
        if not df_export.empty:
            df_export["modo"] = modo
            df_export.to_sql("linhas", conn, if_exists="append", index=False)
        conn.commit()
        return len(df_export)
    finally:
        conn.close()


def load_linhas(modo: str = "ativas", db_path: Optional[Path] = None) -> pd.DataFrame:
    """Carrega linhas do banco. Retorna DataFrame vazio se não houver dados."""
    conn = get_connection(db_path)
    try:
        if _is_postgres():
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT * FROM linhas WHERE COALESCE(modo, modo_operacao) = %s",
                    (modo,),
                )
                rows = cur.fetchall()
                if not rows:
                    return pd.DataFrame()
                col_names = [desc[0] for desc in cur.description]
                df = pd.DataFrame(rows, columns=col_names)
        else:
            df = pd.read_sql_query(
                "SELECT * FROM linhas WHERE modo = ?",
                conn,
                params=(modo,),
            )
            if df.empty:
                return pd.DataFrame()
            df = df.drop(columns=[c for c in df.columns if c in ("id", "criado_em", "modo")], errors="ignore")
        df = df.rename(columns={c: REV_COL_MAP[c] for c in df.columns if c in REV_COL_MAP})
        return df
    finally:
        conn.close()


def save_relacao_ativas(linhas: set[str], db_path: Optional[Path] = None) -> int:
    """Salva conjunto de linhas ativas na relação."""
    if _is_postgres():
        return len(linhas)
    conn = get_connection(db_path)
    try:
        conn.execute("DELETE FROM relacao_ativas")
        for ln in linhas:
            conn.execute("INSERT OR REPLACE INTO relacao_ativas (linha) VALUES (?)", (ln,))
        conn.commit()
        return len(linhas)
    finally:
        conn.close()


def load_relacao_ativas(db_path: Optional[Path] = None) -> frozenset[str]:
    """Carrega conjunto de linhas ativas da relação."""
    if _is_postgres():
        return frozenset()
    conn = get_connection(db_path)
    try:
        rows = conn.execute("SELECT linha FROM relacao_ativas").fetchall()
        return frozenset(r[0] for r in rows if r[0])
    finally:
        conn.close()


def has_data(modo: str = "ativas", db_path: Optional[Path] = None) -> bool:
    """Verifica se existem dados no banco para o modo."""
    conn = get_connection(db_path)
    try:
        if _is_postgres():
            with conn.cursor() as cur:
                cur.execute("SELECT COUNT(*) FROM linhas WHERE COALESCE(modo, modo_operacao) = %s", (modo,))
                return cur.fetchone()[0] > 0
        count = conn.execute("SELECT COUNT(*) FROM linhas WHERE modo = ?", (modo,)).fetchone()[0]
        return count > 0
    finally:
        conn.close()


def registrar_auditoria(
    acao: str,
    entidade: str,
    chave_registro: str = "",
    chamado_id: str = "",
    antes: Optional[dict] = None,
    depois: Optional[dict] = None,
    detalhes: str = "",
    user_id: str = "",
    username: str = "",
    origem: str = "app",
    db_path: Optional[Path] = None,
) -> None:
    """Registra um evento de auditoria."""
    conn = get_connection(db_path)
    try:
        before_json = json.dumps(antes, ensure_ascii=False) if antes is not None else None
        after_json = json.dumps(depois, ensure_ascii=False) if depois is not None else None
        if _is_postgres():
            chamado_val = int(chamado_id) if str(chamado_id or "").strip().isdigit() else None
            user_val = int(user_id) if str(user_id or "").strip().isdigit() else None
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO auditoria
                    (acao, entidade, entidade_id, chamado_id, antes_json, depois_json, detalhes, user_id, username, origem)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    """,
                    (
                        acao,
                        entidade,
                        (chave_registro or "").strip(),
                        chamado_val,
                        before_json,
                        after_json,
                        (detalhes or "").strip(),
                        user_val,
                        (username or "").strip(),
                        (origem or "app").strip(),
                    ),
                )
        else:
            conn.execute(
                """
                INSERT INTO audit_log
                (acao, entidade, chave_registro, chamado_id, antes_json, depois_json, detalhes, user_id, username, origem)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    acao,
                    entidade,
                    (chave_registro or "").strip(),
                    (chamado_id or "").strip(),
                    before_json,
                    after_json,
                    (detalhes or "").strip(),
                    (user_id or "").strip(),
                    (username or "").strip(),
                    (origem or "app").strip(),
                ),
            )
        conn.commit()
    finally:
        conn.close()


def listar_auditoria(
    limit: int = 200,
    username: str = "",
    acao: str = "",
    entidade: str = "",
    chamado_id: str = "",
    db_path: Optional[Path] = None,
) -> list[dict]:
    """Lista eventos de auditoria mais recentes (com filtros opcionais)."""
    conn = get_connection(db_path)
    try:
        clauses: list[str] = []
        params: list[object] = []
        placeholder = "%s" if _is_postgres() else "?"
        if username.strip():
            clauses.append(f"username = {placeholder}")
            params.append(username.strip())
        if acao.strip():
            clauses.append(f"acao = {placeholder}")
            params.append(acao.strip())
        if entidade.strip():
            clauses.append(f"entidade = {placeholder}")
            params.append(entidade.strip())
        if chamado_id.strip():
            if _is_postgres() and chamado_id.strip().isdigit():
                clauses.append(f"chamado_id = {placeholder}")
                params.append(int(chamado_id.strip()))
            elif not _is_postgres():
                clauses.append(f"chamado_id = {placeholder}")
                params.append(chamado_id.strip())
        where_sql = f"WHERE {' AND '.join(clauses)}" if clauses else ""
        if _is_postgres():
            sql = f"""
                SELECT id, acao, entidade, entidade_id AS chave_registro, chamado_id, antes_json, depois_json, detalhes, user_id, username, origem, criado_em
                FROM auditoria
                {where_sql}
                ORDER BY id DESC
                LIMIT {placeholder}
            """
            params.append(max(1, int(limit)))
            with conn.cursor() as cur:
                cur.execute(sql, params)
                rows = cur.fetchall()
        else:
            sql = f"""
                SELECT id, acao, entidade, chave_registro, chamado_id, antes_json, depois_json, detalhes, user_id, username, origem, criado_em
                FROM audit_log
                {where_sql}
                ORDER BY id DESC
                LIMIT {placeholder}
            """
            params.append(max(1, int(limit)))
            rows = conn.execute(sql, params).fetchall()
        return [
            {
                "id": r[0],
                "acao": r[1],
                "entidade": r[2],
                "chave_registro": r[3],
                "chamado_id": r[4],
                "antes_json": r[5],
                "depois_json": r[6],
                "detalhes": r[7],
                "user_id": r[8],
                "username": r[9],
                "origem": r[10],
                "criado_em": r[11],
            }
            for r in rows
        ]
    finally:
        conn.close()


def garantir_chamado_stub(
    chamado_id: str,
    tipo: str = "gerenciamento",
    db_path: Optional[Path] = None,
) -> Optional[int]:
    """
    Garante que exista um registro mínimo na tabela `chamados` (PostgreSQL).

    Objetivo: permitir inserções futuras em tabelas dependentes (ex.: `chamado_eventos`)
    sem violar FKs quando o app recebe `chamado_id` por URL.
    """
    if not _is_postgres():
        return None
    chamado_id = str(chamado_id or "").strip()
    if not chamado_id:
        return None
    chamado_int = int(chamado_id) if chamado_id.isdigit() else None

    conn = get_connection(db_path)
    try:
        with conn.cursor() as cur:
            if chamado_int is not None:
                # Auditoria no app referencia `chamados(id)` usando `chamado_id` como int.
                cur.execute("SELECT id FROM chamados WHERE id = %s", (chamado_int,))
                row = cur.fetchone()
                if row:
                    return int(row[0])

                cur.execute(
                    """
                    INSERT INTO chamados (id, numero_chamado, tipo)
                    VALUES (%s, %s, %s)
                    RETURNING id
                    """,
                    (chamado_int, chamado_id, tipo),
                )
                new_id = cur.fetchone()
                conn.commit()
                return int(new_id[0]) if new_id else None
            else:
                cur.execute("SELECT id FROM chamados WHERE numero_chamado = %s", (chamado_id,))
                row = cur.fetchone()
                if row:
                    return int(row[0])

                cur.execute(
                    """
                    INSERT INTO chamados (numero_chamado, tipo)
                    VALUES (%s, %s)
                    RETURNING id
                    """,
                    (chamado_id, tipo),
                )
                new_id = cur.fetchone()
                conn.commit()
                return int(new_id[0]) if new_id else None
    except UniqueViolation:  # pragma: no cover (caso raro, concorrência)
        with conn.cursor() as cur:
            if chamado_int is not None:
                cur.execute("SELECT id FROM chamados WHERE id = %s", (chamado_int,))
            else:
                cur.execute("SELECT id FROM chamados WHERE numero_chamado = %s", (chamado_id,))
            row = cur.fetchone()
            return int(row[0]) if row else None
    finally:
        conn.close()


def vincular_chamado_linha(
    chamado_id: str,
    linha_num: str,
    db_path: Optional[Path] = None,
) -> None:
    """Vincula `chamados.linha_id` a partir de `linhas.numero_linha` (PostgreSQL)."""
    if not _is_postgres():
        return

    chamado_id = str(chamado_id or "").strip()
    linha_num = str(linha_num or "").strip()
    if not chamado_id or not linha_num:
        return
    chamado_int = int(chamado_id) if chamado_id.isdigit() else None

    conn = get_connection(db_path)
    try:
        with conn.cursor() as cur:
            # Garante que `linha_id` seja nulo quando não encontrar a linha.
            if chamado_int is not None:
                cur.execute(
                    """
                    UPDATE chamados
                    SET linha_id = (
                        SELECT id FROM linhas WHERE numero_linha = %s LIMIT 1
                    )
                    WHERE id = %s
                    """,
                    (linha_num, chamado_int),
                )
            else:
                cur.execute(
                    """
                    UPDATE chamados
                    SET linha_id = (
                        SELECT id FROM linhas WHERE numero_linha = %s LIMIT 1
                    )
                    WHERE numero_chamado = %s
                    """,
                    (linha_num, chamado_id),
                )
        conn.commit()
    finally:
        conn.close()


def _enviar_notificacao_chamado(
    numero_chamado: str,
    titulo: str,
    solicitante_id: str,
    aberto_em: str,
    descricao: str = "",
) -> None:
    """Envia e-mail para todos os admins quando chamado é criado. Falha silenciosa."""
    try:
        from src.services.email_service import send_chamado_notification

        admins = listar_emails_admins()
        if not admins:
            return

        solicitante = "Usuário"
        if solicitante_id and str(solicitante_id).isdigit():
            conn = get_connection()
            try:
                with conn.cursor() as cur:
                    cur.execute(
                        "SELECT username FROM usuarios_app WHERE id = %s",
                        (int(solicitante_id),),
                    )
                    row = cur.fetchone()
                    if row:
                        solicitante = str(row[0])
            finally:
                conn.close()

        aberto_fmt = str(aberto_em)[:19].replace("T", " ") if aberto_em else ""

        send_chamado_notification(
            admins_emails=admins,
            numero_chamado=numero_chamado,
            titulo=titulo,
            solicitante=solicitante,
            aberto_em=aberto_fmt,
            descricao=descricao,
        )
    except Exception:
        pass


def criar_chamado(
    titulo: str,
    descricao: str,
    tipo: str = "gerenciamento",
    prioridade: str = "normal",
    status: str = "aberto",
    linha_num: str = "",
    solicitante_id: str = "",
    origem: str = "app",
    db_path: Optional[Path] = None,
) -> Optional[dict]:
    """Cria chamado no PostgreSQL e retorna payload básico."""
    if not _is_postgres():
        return None

    titulo = str(titulo or "").strip()
    descricao = str(descricao or "").strip()
    tipo = str(tipo or "gerenciamento").strip() or "gerenciamento"
    prioridade = str(prioridade or "normal").strip() or "normal"
    status = str(status or "aberto").strip() or "aberto"
    origem = str(origem or "app").strip() or "app"
    linha_num = str(linha_num or "").strip()
    solicitante_val = int(solicitante_id) if str(solicitante_id or "").strip().isdigit() else None

    conn = get_connection(db_path)
    try:
        with conn.cursor() as cur:
            linha_id = None
            if linha_num:
                cur.execute("SELECT id FROM linhas WHERE numero_linha = %s LIMIT 1", (linha_num,))
                row_linha = cur.fetchone()
                if row_linha:
                    linha_id = int(row_linha[0])

            cur.execute("SELECT COALESCE(MAX(id), 0) + 1 FROM chamados")
            next_num = int(cur.fetchone()[0])
            numero_chamado = str(next_num)

            cur.execute(
                """
                INSERT INTO chamados (
                    numero_chamado, tipo, status, prioridade, origem, titulo, descricao, linha_id, solicitante_id
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                RETURNING id, numero_chamado, tipo, status, prioridade, origem, titulo, descricao, aberto_em, atualizado_em, fechado_em, linha_id
                """,
                (
                    numero_chamado,
                    tipo[:100],
                    status[:50],
                    prioridade[:50],
                    origem[:50],
                    titulo[:255],
                    descricao,
                    linha_id,
                    solicitante_val,
                ),
            )
            row = cur.fetchone()
        conn.commit()
        if not row:
            return None
        resultado = {
            "id": row[0],
            "numero_chamado": row[1],
            "tipo": row[2],
            "status": row[3],
            "prioridade": row[4],
            "origem": row[5],
            "titulo": row[6],
            "descricao": row[7],
            "aberto_em": row[8],
            "atualizado_em": row[9],
            "fechado_em": row[10],
            "linha_id": row[11],
            "linha_numero": linha_num if linha_num else "",
        }
        # Notifica admins por e-mail (falha silenciosa)
        _enviar_notificacao_chamado(
            numero_chamado=str(row[1]),
            titulo=str(row[6]),
            solicitante_id=str(solicitante_val or ""),
            aberto_em=str(row[8]),
            descricao=str(row[7] or ""),
        )
        return resultado
    finally:
        conn.close()


def listar_chamados(
    limit: int = 200,
    status: str = "",
    busca: str = "",
    db_path: Optional[Path] = None,
) -> list[dict]:
    """Lista chamados com filtros simples (PostgreSQL)."""
    if not _is_postgres():
        return []

    limit = max(1, int(limit))
    status = str(status or "").strip().lower()
    busca = str(busca or "").strip()

    clauses: list[str] = []
    params: list[Any] = []

    if status:
        clauses.append("LOWER(c.status) = %s")
        params.append(status)
    if busca:
        clauses.append(
            "(c.numero_chamado ILIKE %s OR c.titulo ILIKE %s OR c.descricao ILIKE %s OR COALESCE(l.numero_linha,'') ILIKE %s)"
        )
        like = f"%{busca}%"
        params.extend([like, like, like, like])

    where_sql = f"WHERE {' AND '.join(clauses)}" if clauses else ""
    sql = f"""
        SELECT
            c.id,
            c.numero_chamado,
            c.tipo,
            c.status,
            c.prioridade,
            c.origem,
            c.titulo,
            c.descricao,
            c.aberto_em,
            c.atualizado_em,
            c.fechado_em,
            c.linha_id,
            l.numero_linha
        FROM chamados c
        LEFT JOIN linhas l ON l.id = c.linha_id
        {where_sql}
        ORDER BY c.id DESC
        LIMIT %s
    """
    params.append(limit)

    conn = get_connection(db_path)
    try:
        with conn.cursor() as cur:
            cur.execute(sql, params)
            rows = cur.fetchall()
        return [
            {
                "id": r[0],
                "numero_chamado": r[1],
                "tipo": r[2],
                "status": r[3],
                "prioridade": r[4],
                "origem": r[5],
                "titulo": r[6],
                "descricao": r[7],
                "aberto_em": r[8],
                "atualizado_em": r[9],
                "fechado_em": r[10],
                "linha_id": r[11],
                "linha_numero": r[12] or "",
            }
            for r in rows
        ]
    finally:
        conn.close()


def obter_chamado(
    chamado_id: str,
    db_path: Optional[Path] = None,
) -> Optional[dict]:
    """Obtém detalhe de um chamado por id/numero_chamado (PostgreSQL)."""
    if not _is_postgres():
        return None

    chamado_id = str(chamado_id or "").strip()
    if not chamado_id:
        return None

    conn = get_connection(db_path)
    try:
        with conn.cursor() as cur:
            if chamado_id.isdigit():
                cur.execute(
                    """
                    SELECT
                        c.id, c.numero_chamado, c.tipo, c.status, c.prioridade, c.origem,
                        c.titulo, c.descricao, c.aberto_em, c.atualizado_em, c.fechado_em,
                        c.linha_id, l.numero_linha
                    FROM chamados c
                    LEFT JOIN linhas l ON l.id = c.linha_id
                    WHERE c.id = %s
                    LIMIT 1
                    """,
                    (int(chamado_id),),
                )
            else:
                cur.execute(
                    """
                    SELECT
                        c.id, c.numero_chamado, c.tipo, c.status, c.prioridade, c.origem,
                        c.titulo, c.descricao, c.aberto_em, c.atualizado_em, c.fechado_em,
                        c.linha_id, l.numero_linha
                    FROM chamados c
                    LEFT JOIN linhas l ON l.id = c.linha_id
                    WHERE c.numero_chamado = %s
                    LIMIT 1
                    """,
                    (chamado_id,),
                )
            row = cur.fetchone()
        if not row:
            return None
        return {
            "id": row[0],
            "numero_chamado": row[1],
            "tipo": row[2],
            "status": row[3],
            "prioridade": row[4],
            "origem": row[5],
            "titulo": row[6],
            "descricao": row[7],
            "aberto_em": row[8],
            "atualizado_em": row[9],
            "fechado_em": row[10],
            "linha_id": row[11],
            "linha_numero": row[12] or "",
        }
    finally:
        conn.close()


def atualizar_status_chamado(
    chamado_id: str,
    novo_status: str,
    db_path: Optional[Path] = None,
) -> bool:
    """Atualiza status de chamado e timestamps (PostgreSQL)."""
    if not _is_postgres():
        return False
    chamado_id = str(chamado_id or "").strip()
    novo_status = str(novo_status or "").strip().lower()
    if not chamado_id or not novo_status:
        return False

    conn = get_connection(db_path)
    try:
        with conn.cursor() as cur:
            if chamado_id.isdigit():
                cur.execute(
                    """
                    UPDATE chamados
                    SET status = %s,
                        atualizado_em = NOW(),
                        fechado_em = CASE WHEN %s IN ('fechado', 'encerrado', 'closed') THEN NOW() ELSE fechado_em END
                    WHERE id = %s
                    """,
                    (novo_status[:50], novo_status, int(chamado_id)),
                )
            else:
                cur.execute(
                    """
                    UPDATE chamados
                    SET status = %s,
                        atualizado_em = NOW(),
                        fechado_em = CASE WHEN %s IN ('fechado', 'encerrado', 'closed') THEN NOW() ELSE fechado_em END
                    WHERE numero_chamado = %s
                    """,
                    (novo_status[:50], novo_status, chamado_id),
                )
            ok = cur.rowcount > 0
        conn.commit()
        return ok
    finally:
        conn.close()


def registrar_chamado_evento(
    chamado_id: str,
    tipo_evento: str,
    descricao: str = "",
    antes: Optional[dict] = None,
    depois: Optional[dict] = None,
    user_id: str = "",
    db_path: Optional[Path] = None,
) -> None:
    """
    Registra evento em `chamado_eventos` (PostgreSQL) para unificação futura.
    """
    if not _is_postgres():
        return
    chamado_id = str(chamado_id or "").strip()
    if not chamado_id:
        return
    if not chamado_id.isdigit():
        return

    chamado_val = int(chamado_id)
    user_val = int(user_id) if str(user_id or "").strip().isdigit() else None

    tipo_evento = str(tipo_evento or "").strip()
    if not tipo_evento:
        tipo_evento = "evento"

    conn = get_connection(db_path)
    try:
        before_json = json.dumps(antes, ensure_ascii=False, default=str) if antes is not None else None
        after_json = json.dumps(depois, ensure_ascii=False, default=str) if depois is not None else None
        with conn.cursor() as cur:
            if user_val is not None:
                cur.execute("SELECT 1 FROM usuarios_app WHERE id = %s LIMIT 1", (user_val,))
                if not cur.fetchone():
                    user_val = None
            cur.execute(
                """
                INSERT INTO chamado_eventos (chamado_id, tipo_evento, descricao, antes_json, depois_json, criado_por)
                VALUES (%s, %s, %s, %s, %s, %s)
                """,
                (chamado_val, tipo_evento[:100], (descricao or "").strip(), before_json, after_json, user_val),
            )
        conn.commit()
    finally:
        conn.close()


def registrar_movimentacao_linha(
    chamado_id: str,
    linha_num: str,
    tipo_movimentacao: str,
    antes: Optional[dict] = None,
    depois: Optional[dict] = None,
    motivo: str = "",
    observacao: str = "",
    user_id: str = "",
    db_path: Optional[Path] = None,
) -> None:
    """
    Registra movimentação estruturada em `movimentacoes_linha` (PostgreSQL).
    """
    if not _is_postgres():
        return
    chamado_id = str(chamado_id or "").strip()
    linha_num = str(linha_num or "").strip()
    if not chamado_id or not linha_num:
        return
    if not chamado_id.isdigit():
        return

    chamado_val = int(chamado_id)
    user_val = int(user_id) if str(user_id or "").strip().isdigit() else None
    tipo_mov = str(tipo_movimentacao or "").strip() or "movimentacao"

    conn = get_connection(db_path)
    try:
        before_json = json.dumps(antes, ensure_ascii=False, default=str) if antes is not None else None
        after_json = json.dumps(depois, ensure_ascii=False, default=str) if depois is not None else None

        with conn.cursor() as cur:
            cur.execute(
                "SELECT id FROM linhas WHERE numero_linha = %s LIMIT 1",
                (linha_num,),
            )
            row = cur.fetchone()
            if not row:
                return
            linha_id = int(row[0])

            if user_val is not None:
                cur.execute("SELECT 1 FROM usuarios_app WHERE id = %s LIMIT 1", (user_val,))
                if not cur.fetchone():
                    user_val = None

            cur.execute(
                """
                INSERT INTO movimentacoes_linha (
                    linha_id,
                    chamado_id,
                    tipo_movimentacao,
                    antes_json,
                    depois_json,
                    motivo,
                    observacao,
                    executado_por
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                """,
                (
                    linha_id,
                    chamado_val,
                    tipo_mov[:100],
                    before_json,
                    after_json,
                    (motivo or "").strip(),
                    (observacao or "").strip(),
                    user_val,
                ),
            )
        conn.commit()
    finally:
        conn.close()


# ─────────────────────────────────────────────────────────────
# user_column_prefs
# ─────────────────────────────────────────────────────────────

def salvar_colunas_visiveis(usuario_id: int, colunas: list, db_path=None) -> None:
    """Persiste preferência de colunas visíveis do usuário."""
    if not _is_postgres():
        return
    conn = get_connection(db_path)
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO user_column_prefs (usuario_id, colunas_visiveis, atualizado_em)
                VALUES (%s, %s, NOW())
                ON CONFLICT (usuario_id) DO UPDATE
                    SET colunas_visiveis = EXCLUDED.colunas_visiveis,
                        atualizado_em = NOW()
                """,
                (usuario_id, json.dumps(colunas, ensure_ascii=False)),
            )
        conn.commit()
    finally:
        conn.close()


def carregar_colunas_visiveis(usuario_id: int, db_path=None) -> list:
    """Retorna lista de colunas visíveis salvas; [] se não houver preferência."""
    if not _is_postgres():
        return []
    conn = get_connection(db_path)
    try:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT colunas_visiveis FROM user_column_prefs WHERE usuario_id = %s",
                (usuario_id,),
            )
            row = cur.fetchone()
        if not row:
            return []
        val = row[0]
        if isinstance(val, list):
            return val
        try:
            return json.loads(val)
        except Exception:
            return []
    finally:
        conn.close()


# ─────────────────────────────────────────────────────────────
# filtros_salvos
# ─────────────────────────────────────────────────────────────

def salvar_filtro(usuario_id: int, nome: str, filtro: dict, db_path=None) -> int:
    """Salva filtro nomeado e retorna id gerado."""
    if not _is_postgres():
        return -1
    conn = get_connection(db_path)
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO filtros_salvos (usuario_id, nome, filtro_json)
                VALUES (%s, %s, %s)
                RETURNING id
                """,
                (usuario_id, nome[:100], json.dumps(filtro, ensure_ascii=False)),
            )
            new_id = cur.fetchone()
        conn.commit()
        return int(new_id[0]) if new_id else -1
    finally:
        conn.close()


def listar_filtros(usuario_id: int, db_path=None) -> list:
    """Lista filtros salvos do usuário."""
    if not _is_postgres():
        return []
    conn = get_connection(db_path)
    try:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT id, nome, filtro_json, criado_em FROM filtros_salvos WHERE usuario_id = %s ORDER BY id",
                (usuario_id,),
            )
            rows = cur.fetchall()
        result = []
        for r in rows:
            filtro_val = r[2]
            if isinstance(filtro_val, dict):
                filtro_dict = filtro_val
            else:
                try:
                    filtro_dict = json.loads(filtro_val)
                except Exception:
                    filtro_dict = {}
            result.append({"id": r[0], "nome": r[1], "filtro": filtro_dict, "criado_em": r[3]})
        return result
    finally:
        conn.close()


def excluir_filtro(filtro_id: int, usuario_id: int, db_path=None) -> bool:
    """Remove filtro (somente do próprio usuário)."""
    if not _is_postgres():
        return False
    conn = get_connection(db_path)
    try:
        with conn.cursor() as cur:
            cur.execute(
                "DELETE FROM filtros_salvos WHERE id = %s AND usuario_id = %s",
                (filtro_id, usuario_id),
            )
            ok = cur.rowcount > 0
        conn.commit()
        return ok
    finally:
        conn.close()


# ─────────────────────────────────────────────────────────────
# line_flags
# ─────────────────────────────────────────────────────────────

def salvar_flag_linha(linha_id: int, usuario_id: int, cor: str = "yellow", nota: str = "", db_path=None) -> None:
    """Cria ou atualiza flag de cor/nota em uma linha."""
    if not _is_postgres():
        return
    conn = get_connection(db_path)
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO line_flags (linha_id, usuario_id, cor, nota)
                VALUES (%s, %s, %s, %s)
                ON CONFLICT (linha_id, usuario_id) DO UPDATE
                    SET cor = EXCLUDED.cor,
                        nota = EXCLUDED.nota
                """,
                (linha_id, usuario_id, (cor or "yellow")[:20], (nota or "").strip()),
            )
        conn.commit()
    finally:
        conn.close()


def remover_flag_linha(linha_id: int, usuario_id: int, db_path=None) -> bool:
    """Remove flag de uma linha."""
    if not _is_postgres():
        return False
    conn = get_connection(db_path)
    try:
        with conn.cursor() as cur:
            cur.execute(
                "DELETE FROM line_flags WHERE linha_id = %s AND usuario_id = %s",
                (linha_id, usuario_id),
            )
            ok = cur.rowcount > 0
        conn.commit()
        return ok
    finally:
        conn.close()


def listar_flags_usuario(usuario_id: int, db_path=None) -> dict:
    """Retorna dict {linha_id: {cor, nota}} para o usuário."""
    if not _is_postgres():
        return {}
    conn = get_connection(db_path)
    try:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT linha_id, cor, nota FROM line_flags WHERE usuario_id = %s",
                (usuario_id,),
            )
            rows = cur.fetchall()
        return {int(r[0]): {"cor": r[1], "nota": r[2] or ""} for r in rows}
    finally:
        conn.close()


# ─────────────────────────────────────────────────────────────
# equipes_config
# ─────────────────────────────────────────────────────────────

def listar_equipes_config(db_path=None) -> list:
    """Lista equipes cadastradas no sistema."""
    if not _is_postgres():
        return []
    conn = get_connection(db_path)
    try:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT id, nome, segmento, gestor, setor, ativo, criado_em FROM equipes_config ORDER BY nome"
            )
            rows = cur.fetchall()
        return [
            {"id": r[0], "nome": r[1], "segmento": r[2], "gestor": r[3],
             "setor": r[4], "ativo": r[5], "criado_em": r[6]}
            for r in rows
        ]
    finally:
        conn.close()


def salvar_equipe_config(nome: str, segmento: str, gestor: str = "", setor: str = "",
                         ativo: bool = True, equipe_id: int = None, db_path=None) -> int:
    """Cria ou atualiza equipe. Retorna id."""
    if not _is_postgres():
        return -1
    conn = get_connection(db_path)
    try:
        with conn.cursor() as cur:
            if equipe_id:
                cur.execute(
                    """
                    UPDATE equipes_config
                    SET nome=%s, segmento=%s, gestor=%s, setor=%s, ativo=%s
                    WHERE id=%s
                    RETURNING id
                    """,
                    (nome[:150], segmento[:100], gestor[:255], setor[:255], ativo, equipe_id),
                )
            else:
                cur.execute(
                    """
                    INSERT INTO equipes_config (nome, segmento, gestor, setor, ativo)
                    VALUES (%s, %s, %s, %s, %s)
                    RETURNING id
                    """,
                    (nome[:150], segmento[:100], gestor[:255], setor[:255], ativo),
                )
            row = cur.fetchone()
        conn.commit()
        return int(row[0]) if row else -1
    finally:
        conn.close()


def excluir_equipe_config(equipe_id: int, db_path=None) -> bool:
    """Remove equipe pelo id."""
    if not _is_postgres():
        return False
    conn = get_connection(db_path)
    try:
        with conn.cursor() as cur:
            cur.execute("DELETE FROM equipes_config WHERE id = %s", (equipe_id,))
            ok = cur.rowcount > 0
        conn.commit()
        return ok
    finally:
        conn.close()


# ─────────────────────────────────────────────────────────────
# gestores_config
# ─────────────────────────────────────────────────────────────

def listar_gestores_config(db_path=None) -> list:
    """Lista gestores/gerência cadastrados."""
    if not _is_postgres():
        return []
    conn = get_connection(db_path)
    try:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT id, nome, equipe, segmento, email, ativo FROM gestores_config ORDER BY nome"
            )
            rows = cur.fetchall()
        return [
            {"id": r[0], "nome": r[1], "equipe": r[2], "segmento": r[3],
             "email": r[4], "ativo": r[5]}
            for r in rows
        ]
    finally:
        conn.close()


def salvar_gestor_config(nome: str, equipe: str = "", segmento: str = "", email: str = "",
                         ativo: bool = True, gestor_id: int = None, db_path=None) -> int:
    """Cria ou atualiza gestor. Retorna id."""
    if not _is_postgres():
        return -1
    conn = get_connection(db_path)
    try:
        with conn.cursor() as cur:
            if gestor_id:
                cur.execute(
                    """
                    UPDATE gestores_config
                    SET nome=%s, equipe=%s, segmento=%s, email=%s, ativo=%s
                    WHERE id=%s
                    RETURNING id
                    """,
                    (nome[:255], equipe[:150], segmento[:100], email[:255], ativo, gestor_id),
                )
            else:
                cur.execute(
                    """
                    INSERT INTO gestores_config (nome, equipe, segmento, email, ativo)
                    VALUES (%s, %s, %s, %s, %s)
                    RETURNING id
                    """,
                    (nome[:255], equipe[:150], segmento[:100], email[:255], ativo),
                )
            row = cur.fetchone()
        conn.commit()
        return int(row[0]) if row else -1
    finally:
        conn.close()


def excluir_gestor_config(gestor_id: int, db_path=None) -> bool:
    """Remove gestor pelo id."""
    if not _is_postgres():
        return False
    conn = get_connection(db_path)
    try:
        with conn.cursor() as cur:
            cur.execute("DELETE FROM gestores_config WHERE id = %s", (gestor_id,))
            ok = cur.rowcount > 0
        conn.commit()
        return ok
    finally:
        conn.close()


def listar_equipes_da_tabela(db_path=None) -> list:
    """Retorna equipes distintas com seus gestores/supervisores atuais da tabela linhas."""
    if not _is_postgres():
        return []
    conn = get_connection(db_path)
    try:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT
                    equipe_padrao,
                    MAX(gestor)       AS gestor,
                    MAX(supervisor)   AS supervisor,
                    MAX(grupo_equipe) AS segmento
                FROM linhas
                WHERE modo = 'ativas'
                  AND equipe_padrao IS NOT NULL
                  AND equipe_padrao <> ''
                GROUP BY equipe_padrao
                ORDER BY equipe_padrao
            """)
            rows = cur.fetchall()
            return [
                {"equipe": r[0], "gestor": r[1] or "", "supervisor": r[2] or "", "segmento": r[3] or ""}
                for r in rows
            ]
    finally:
        conn.close()


def atualizar_gestor_equipe(equipe_padrao: str, novo_gestor: str, novo_supervisor: str, db_path=None) -> int:
    """Atualiza gestor e supervisor de todas as linhas de uma equipe. Retorna nº de linhas afetadas."""
    if not _is_postgres():
        return 0
    conn = get_connection(db_path)
    try:
        with conn.cursor() as cur:
            cur.execute(
                "UPDATE linhas SET gestor = %s, supervisor = %s WHERE equipe_padrao = %s",
                (novo_gestor or None, novo_supervisor or None, equipe_padrao),
            )
            affected = cur.rowcount
        conn.commit()
        return affected
    finally:
        conn.close()


def criar_equipe_na_tabela(equipe_padrao: str, grupo_equipe: str, gestor: str = "", supervisor: str = "", db_path=None) -> bool:
    """Verifica se equipe já existe; se não, cria uma linha placeholder para registrá-la."""
    if not _is_postgres():
        return False
    conn = get_connection(db_path)
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT 1 FROM linhas WHERE equipe_padrao = %s LIMIT 1", (equipe_padrao,))
            if cur.fetchone():
                return False  # já existe
            cur.execute(
                """INSERT INTO linhas (linha, nome, equipe_padrao, grupo_equipe, gestor, supervisor, modo)
                   VALUES (%s, %s, %s, %s, %s, %s, 'ativas')""",
                (f"PLACEHOLDER-{equipe_padrao[:8].upper()}", "VAGO", equipe_padrao, grupo_equipe, gestor or None, supervisor or None),
            )
        conn.commit()
        return True
    finally:
        conn.close()


# ── Gestores (tabela linhas) ──────────────────────────────────────────────────

def listar_gestores_da_tabela(db_path=None) -> list:
    """Retorna gestores distintos com as equipes que gerenciam."""
    if not _is_postgres():
        return []
    conn = get_connection(db_path)
    try:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT gestor,
                       COUNT(DISTINCT equipe_padrao) AS n_equipes,
                       STRING_AGG(DISTINCT equipe_padrao, ', ' ORDER BY equipe_padrao) AS equipes
                FROM linhas
                WHERE gestor IS NOT NULL AND gestor <> '' AND modo = 'ativas'
                GROUP BY gestor
                ORDER BY gestor
            """)
            return [{"gestor": r[0], "n_equipes": r[1], "equipes": r[2] or ""} for r in cur.fetchall()]
    finally:
        conn.close()


def renomear_gestor(gestor_antigo: str, gestor_novo: str, db_path=None) -> int:
    """Renomeia gestor em todas as linhas. Retorna nº de linhas afetadas."""
    if not _is_postgres() or not gestor_novo.strip():
        return 0
    conn = get_connection(db_path)
    try:
        with conn.cursor() as cur:
            cur.execute("UPDATE linhas SET gestor = %s WHERE gestor = %s", (gestor_novo.strip(), gestor_antigo))
            n = cur.rowcount
        conn.commit()
        return n
    finally:
        conn.close()


def renomear_equipe(equipe_antiga: str, equipe_nova: str, db_path=None) -> int:
    """Renomeia equipe em todas as linhas. Retorna nº de linhas afetadas."""
    if not _is_postgres() or not equipe_nova.strip():
        return 0
    conn = get_connection(db_path)
    try:
        with conn.cursor() as cur:
            cur.execute("UPDATE linhas SET equipe_padrao = %s WHERE equipe_padrao = %s", (equipe_nova.strip(), equipe_antiga))
            n = cur.rowcount
        conn.commit()
        return n
    finally:
        conn.close()


def desativar_equipe(equipe_padrao: str, db_path=None) -> int:
    """Move todas as linhas ativas da equipe para modo='desativadas'. Retorna nº afetadas."""
    if not _is_postgres():
        return 0
    conn = get_connection(db_path)
    try:
        with conn.cursor() as cur:
            cur.execute(
                "UPDATE linhas SET modo = 'desativadas' WHERE equipe_padrao = %s AND modo = 'ativas'",
                (equipe_padrao,),
            )
            n = cur.rowcount
        conn.commit()
        return n
    finally:
        conn.close()


def excluir_equipe(equipe_padrao: str, db_path=None) -> int:
    """Exclui TODAS as linhas da equipe (ativas e desativadas). Retorna nº excluídas."""
    if not _is_postgres():
        return 0
    conn = get_connection(db_path)
    try:
        with conn.cursor() as cur:
            cur.execute("DELETE FROM linhas WHERE equipe_padrao = %s", (equipe_padrao,))
            n = cur.rowcount
        conn.commit()
        return n
    finally:
        conn.close()


def contar_linhas_equipe(equipe_padrao: str, db_path=None) -> dict:
    """Retorna {'ativas': int, 'desativadas': int} para a equipe."""
    if not _is_postgres():
        return {"ativas": 0, "desativadas": 0}
    conn = get_connection(db_path)
    try:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT modo, COUNT(*) FROM linhas WHERE equipe_padrao = %s GROUP BY modo",
                (equipe_padrao,),
            )
            result = {"ativas": 0, "desativadas": 0}
            for row in cur.fetchall():
                if row[0] in result:
                    result[row[0]] = row[1]
            return result
    finally:
        conn.close()


# ── Usuários unificados (usuarios_app + users) ────────────────────────────────

def listar_usuarios_unificado(db_path=None) -> list:
    """
    Lista usuários de ambos os sistemas.
    Faz o cruzamento via Python após buscar cada tabela separadamente.
    """
    if not _is_postgres():
        return []
    conn = get_connection(db_path)
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT id, username, email, is_admin, ativo FROM usuarios_app ORDER BY username")
            gerenc_rows = cur.fetchall()
            cur.execute("SELECT id, name, email, role, is_active FROM users ORDER BY name")
            chamados_rows = cur.fetchall()
    finally:
        conn.close()

    # Indexar Chamados por nome normalizado e por e-mail
    cham_by_name  = {(r[1] or "").strip().lower(): r for r in chamados_rows}
    cham_by_email = {(r[2] or "").strip().lower(): r for r in chamados_rows if r[2]}

    results = []
    matched_cham_ids = set()

    for g in gerenc_rows:
        g_id, g_user, g_email, g_admin, g_ativo = g
        key_name  = (g_user  or "").strip().lower()
        key_email = (g_email or "").strip().lower()
        c = cham_by_name.get(key_name) or (cham_by_email.get(key_email) if key_email else None)
        if c:
            matched_cham_ids.add(c[0])
        results.append({
            "id_gerenc":      g_id,
            "username":       g_user,
            "email_gerenc":   g_email,
            "admin_gerenc":   g_admin,
            "ativo_gerenc":   g_ativo,
            "id_chamados":    c[0]   if c else None,
            "name_chamados":  c[1]   if c else None,
            "email_chamados": c[2]   if c else None,
            "role_chamados":  c[3]   if c else None,
            "ativo_chamados": c[4]   if c else None,
        })

    # Usuários que só existem no Chamados
    for c in chamados_rows:
        if c[0] not in matched_cham_ids:
            results.append({
                "id_gerenc":      None,
                "username":       None,
                "email_gerenc":   None,
                "admin_gerenc":   None,
                "ativo_gerenc":   None,
                "id_chamados":    c[0],
                "name_chamados":  c[1],
                "email_chamados": c[2],
                "role_chamados":  c[3],
                "ativo_chamados": c[4],
            })

    results.sort(key=lambda r: (r.get("username") or r.get("name_chamados") or "").lower())
    return results


def criar_usuario_unificado(username: str, email: str, password: str, is_admin: bool = False, db_path=None) -> dict:
    """
    Cria usuário nos dois sistemas (usuarios_app + users).
    Retorna {'gerenc': bool, 'chamados': bool}.
    """
    import logging as _log
    import bcrypt as _bcrypt
    _logger = _log.getLogger(__name__)
    conn = get_connection(db_path)
    result = {"gerenc": False, "chamados": False}
    hash_gerenc = _hash_password(password)
    hash_chamados = _bcrypt.hashpw(password.encode(), _bcrypt.gensalt(12)).decode()
    try:
        with conn.cursor() as cur:
            # usuarios_app
            try:
                cur.execute(
                    """INSERT INTO usuarios_app (username, email, password_hash, salt, is_admin, ativo)
                       VALUES (%s, %s, %s, %s, %s, TRUE)""",
                    (username.strip().lower(), email.strip() or None, hash_gerenc, "", is_admin),
                )
                result["gerenc"] = True
            except Exception as e:
                _logger.error("criar_usuario_unificado — usuarios_app: %s", e, exc_info=True)
                conn.rollback()
            # users (Chamados)
            role = "ADMIN" if is_admin else "USER"
            try:
                cur.execute(
                    """INSERT INTO users (name, email, password_hash, role, is_active)
                       VALUES (%s, %s, %s, %s, TRUE)""",
                    (username.strip(), email.strip() or None, hash_chamados, role),
                )
                result["chamados"] = True
            except Exception as e:
                _logger.error("criar_usuario_unificado — users: %s", e, exc_info=True)
                conn.rollback()
        conn.commit()
    finally:
        conn.close()
    return result


def atualizar_senha_unificada(username: str, nova_senha: str, db_path=None) -> dict:
    """Atualiza senha em ambos os sistemas. Retorna {'gerenc': bool, 'chamados': bool}."""
    import bcrypt as _bcrypt
    conn = get_connection(db_path)
    result = {"gerenc": False, "chamados": False}
    hash_gerenc = _hash_password(nova_senha)
    hash_chamados = _bcrypt.hashpw(nova_senha.encode(), _bcrypt.gensalt(12)).decode()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "UPDATE usuarios_app SET password_hash = %s, salt = %s WHERE LOWER(username) = LOWER(%s)",
                (hash_gerenc, "", username),
            )
            result["gerenc"] = cur.rowcount > 0
            cur.execute(
                "UPDATE users SET password_hash = %s WHERE LOWER(name) = LOWER(%s)",
                (hash_chamados, username),
            )
            result["chamados"] = cur.rowcount > 0
        conn.commit()
    finally:
        conn.close()
    return result


def alternar_admin_unificado(username: str, is_admin: bool, db_path=None) -> None:
    """Alterna flag admin/role em ambos os sistemas."""
    if not _is_postgres():
        return
    conn = get_connection(db_path)
    role = "admin" if is_admin else "technician"
    try:
        with conn.cursor() as cur:
            cur.execute("UPDATE usuarios_app SET is_admin = %s WHERE LOWER(username) = LOWER(%s)", (is_admin, username))
            cur.execute("UPDATE users SET role = %s WHERE LOWER(name) = LOWER(%s)", (role, username))
        conn.commit()
    finally:
        conn.close()


def desativar_usuario_unificado(username: str, ativar: bool = False, db_path=None) -> dict:
    """
    Desativa (ou reativa) um usuário em ambos os sistemas.
    Retorna {'gerenc': bool, 'chamados': bool} indicando onde houve alteração.
    """
    if not _is_postgres():
        return {"gerenc": False, "chamados": False}
    conn = get_connection(db_path)
    resultado = {"gerenc": False, "chamados": False}
    try:
        with conn.cursor() as cur:
            cur.execute(
                "UPDATE usuarios_app SET ativo = %s WHERE LOWER(username) = LOWER(%s)",
                (ativar, username),
            )
            resultado["gerenc"] = cur.rowcount > 0
            cur.execute(
                "UPDATE users SET is_active = %s WHERE LOWER(name) = LOWER(%s)",
                (ativar, username),
            )
            resultado["chamados"] = cur.rowcount > 0
        conn.commit()
    finally:
        conn.close()
    return resultado


def excluir_usuario_unificado(username: str, db_path=None) -> dict:
    """
    Remove permanentemente um usuário de ambos os sistemas.
    Retorna {'gerenc': bool, 'chamados': bool} indicando onde foi excluído.
    """
    if not _is_postgres():
        return {"gerenc": False, "chamados": False}
    conn = get_connection(db_path)
    resultado = {"gerenc": False, "chamados": False}
    try:
        with conn.cursor() as cur:
            cur.execute("DELETE FROM usuarios_app WHERE LOWER(username) = LOWER(%s)", (username,))
            resultado["gerenc"] = cur.rowcount > 0
            cur.execute("DELETE FROM users WHERE LOWER(name) = LOWER(%s)", (username,))
            resultado["chamados"] = cur.rowcount > 0
        conn.commit()
    finally:
        conn.close()
    return resultado
