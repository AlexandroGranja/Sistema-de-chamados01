"""add userrole requester for portal cadastro

Revision ID: c9a8b7d6e5f4
Revises: be7db1ae8459
Create Date: 2026-02-23

"""
from alembic import op


revision = "c9a8b7d6e5f4"
down_revision = "be7db1ae8459"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name != "postgresql":
        return
    # Enum nativo PostgreSQL (SQLAlchemy Enum(UserRole)); nome típico: userrole
    op.execute(
        """
        DO $$ BEGIN
            ALTER TYPE userrole ADD VALUE 'requester';
        EXCEPTION
            WHEN duplicate_object THEN NULL;
        END $$;
        """
    )


def downgrade() -> None:
    # Remover valor de ENUM no PostgreSQL é trabalhoso; deixamos documentado.
    pass
