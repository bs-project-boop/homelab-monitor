"""collector run metadata

Revision ID: 0002_collector_runs
Revises: 0001_initial_inventory
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB

revision = "0002_collector_runs"
down_revision = "0001_initial_inventory"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "collector_runs",
        sa.Column("id", sa.Text(), primary_key=True),
        sa.Column("status", sa.Text(), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("resource_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("error_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("errors", JSONB(), nullable=False, server_default=sa.text("'[]'::jsonb")),
    )
    op.create_index("ix_collector_runs_status_started", "collector_runs", ["status", "started_at"])


def downgrade() -> None:
    op.drop_index("ix_collector_runs_status_started", table_name="collector_runs")
    op.drop_table("collector_runs")
