"""normalized logs

Revision ID: 0004_logs
Revises: 0003_incidents
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB

revision = "0004_logs"
down_revision = "0003_incidents"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "logs",
        sa.Column("id", sa.Text(), primary_key=True),
        sa.Column("resource_id", sa.Text(), sa.ForeignKey("resources.id", ondelete="CASCADE")),
        sa.Column("source", sa.Text(), nullable=False),
        sa.Column("level", sa.Text(), nullable=False),
        sa.Column("message", sa.Text(), nullable=False),
        sa.Column("fingerprint", sa.Text(), nullable=False),
        sa.Column("observed_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("metadata", JSONB, nullable=False, server_default=sa.text("'{}'::jsonb")),
    )
    op.create_index("ix_logs_resource_observed", "logs", ["resource_id", "observed_at"])
    op.create_index("ix_logs_source_observed", "logs", ["source", "observed_at"])
    op.create_unique_constraint("uq_logs_fingerprint", "logs", ["fingerprint"])


def downgrade() -> None:
    op.drop_constraint("uq_logs_fingerprint", "logs", type_="unique")
    op.drop_index("ix_logs_source_observed", table_name="logs")
    op.drop_index("ix_logs_resource_observed", table_name="logs")
    op.drop_table("logs")
