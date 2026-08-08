"""incident lifecycle

Revision ID: 0003_incidents
Revises: 0002_collector_runs
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB

revision = "0003_incidents"
down_revision = "0002_collector_runs"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "incidents",
        sa.Column("id", sa.Text(), primary_key=True),
        sa.Column("resource_id", sa.Text(), sa.ForeignKey("resources.id", ondelete="CASCADE"), nullable=False),
        sa.Column("fingerprint", sa.Text(), nullable=False),
        sa.Column("status", sa.Text(), nullable=False),
        sa.Column("severity", sa.Text(), nullable=False),
        sa.Column("title", sa.Text(), nullable=False),
        sa.Column("opened_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_seen_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("metadata", JSONB(), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.UniqueConstraint("resource_id", "fingerprint", name="uq_incidents_resource_fingerprint"),
    )
    op.create_index("ix_incidents_status_last_seen", "incidents", ["status", "last_seen_at"])


def downgrade() -> None:
    op.drop_index("ix_incidents_status_last_seen", table_name="incidents")
    op.drop_table("incidents")
