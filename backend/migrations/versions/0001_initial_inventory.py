"""initial inventory and status history

Revision ID: 0001_initial_inventory
Revises:
Create Date: 2026-08-06
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "0001_initial_inventory"
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "resources",
        sa.Column("id", sa.Text(), nullable=False),
        sa.Column("kind", sa.Text(), nullable=False),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("source", sa.Text(), nullable=False),
        sa.Column("status", sa.Text(), nullable=False),
        sa.Column("parent_id", sa.Text(), nullable=True),
        sa.Column("address", sa.Text(), nullable=True),
        sa.Column("metadata", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("observed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.ForeignKeyConstraint(["parent_id"], ["resources.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.CheckConstraint("status IN ('unknown', 'up', 'degraded', 'down', 'recovering', 'maintenance')", name="ck_resources_status"),
    )
    op.create_index("ix_resources_parent_id", "resources", ["parent_id"])
    op.create_index("ix_resources_status", "resources", ["status"])
    op.create_index("ix_resources_source_kind", "resources", ["source", "kind"])

    op.create_table(
        "status_events",
        sa.Column("id", sa.BigInteger(), sa.Identity(), nullable=False),
        sa.Column("resource_id", sa.Text(), nullable=False),
        sa.Column("previous_status", sa.Text(), nullable=True),
        sa.Column("status", sa.Text(), nullable=False),
        sa.Column("reason", sa.Text(), nullable=False),
        sa.Column("observed_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("metadata", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.ForeignKeyConstraint(["resource_id"], ["resources.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.CheckConstraint("status IN ('unknown', 'up', 'degraded', 'down', 'recovering', 'maintenance')", name="ck_status_events_status"),
    )
    op.create_index("ix_status_events_resource_time", "status_events", ["resource_id", "observed_at"])


def downgrade() -> None:
    op.drop_index("ix_status_events_resource_time", table_name="status_events")
    op.drop_table("status_events")
    op.drop_index("ix_resources_source_kind", table_name="resources")
    op.drop_index("ix_resources_status", table_name="resources")
    op.drop_index("ix_resources_parent_id", table_name="resources")
    op.drop_table("resources")
