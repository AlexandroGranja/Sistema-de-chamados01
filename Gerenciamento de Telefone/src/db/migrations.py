"""Migrations idempotentes para novas tabelas do redesign."""
from __future__ import annotations
import logging

logger = logging.getLogger(__name__)


def run_migrations(conn) -> None:
    """Executa todas as migrations. Conexão já com cursor psycopg ativo."""
    _create_equipes_config(conn)
    _create_gestores_config(conn)
    _create_filtros_salvos(conn)
    _create_user_column_prefs(conn)
    _create_line_flags(conn)
    _create_password_reset_tokens(conn)


def _create_equipes_config(conn) -> None:
    conn.execute("""
        CREATE TABLE IF NOT EXISTS equipes_config (
            id SERIAL PRIMARY KEY,
            nome VARCHAR(150) NOT NULL,
            segmento VARCHAR(100) NOT NULL,
            gestor VARCHAR(255),
            setor VARCHAR(255),
            ativo BOOLEAN NOT NULL DEFAULT TRUE,
            criado_em TIMESTAMPTZ NOT NULL DEFAULT NOW()
        )
    """)


def _create_gestores_config(conn) -> None:
    conn.execute("""
        CREATE TABLE IF NOT EXISTS gestores_config (
            id SERIAL PRIMARY KEY,
            nome VARCHAR(255) NOT NULL,
            equipe VARCHAR(150),
            segmento VARCHAR(100),
            email VARCHAR(255),
            ativo BOOLEAN NOT NULL DEFAULT TRUE
        )
    """)


def _create_filtros_salvos(conn) -> None:
    conn.execute("""
        CREATE TABLE IF NOT EXISTS filtros_salvos (
            id SERIAL PRIMARY KEY,
            usuario_id INTEGER NOT NULL,
            nome VARCHAR(100) NOT NULL,
            filtro_json JSONB NOT NULL,
            criado_em TIMESTAMPTZ NOT NULL DEFAULT NOW()
        )
    """)


def _create_user_column_prefs(conn) -> None:
    conn.execute("""
        CREATE TABLE IF NOT EXISTS user_column_prefs (
            usuario_id INTEGER PRIMARY KEY,
            colunas_visiveis JSONB NOT NULL DEFAULT '[]',
            atualizado_em TIMESTAMPTZ NOT NULL DEFAULT NOW()
        )
    """)


def _create_line_flags(conn) -> None:
    conn.execute("""
        CREATE TABLE IF NOT EXISTS line_flags (
            id SERIAL PRIMARY KEY,
            linha_id BIGINT NOT NULL,
            usuario_id INTEGER NOT NULL,
            cor VARCHAR(20) NOT NULL DEFAULT 'yellow',
            nota TEXT,
            criado_em TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            UNIQUE(linha_id, usuario_id)
        )
    """)


def _create_password_reset_tokens(conn) -> None:
    conn.execute("""
        CREATE TABLE IF NOT EXISTS password_reset_tokens (
            id SERIAL PRIMARY KEY,
            usuario_id INTEGER NOT NULL,
            token VARCHAR(64) NOT NULL UNIQUE,
            expira_em TIMESTAMPTZ NOT NULL,
            usado_em TIMESTAMPTZ,
            criado_em TIMESTAMPTZ NOT NULL DEFAULT NOW()
        )
    """)
    conn.execute("""
        CREATE INDEX IF NOT EXISTS idx_reset_tokens_token
        ON password_reset_tokens(token)
        WHERE usado_em IS NULL
    """)
