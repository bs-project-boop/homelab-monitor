"""add operational query indexes

Revision ID: 0005
Revises: 0004_logs
"""

from alembic import op

revision = "0005_operational_indexes"
down_revision = "0004_logs"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_index("ix_logs_resource_id", "logs", ["resource_id"])
    op.create_index("ix_logs_observed_at", "logs", ["observed_at"])
    op.create_index("ix_status_events_resource_id", "status_events", ["resource_id"])
    op.create_index("ix_status_events_observed_at", "status_events", ["observed_at"])
    op.create_index("ix_incidents_status", "incidents", ["status"])
    op.create_index("ix_incidents_last_seen_at", "incidents", ["last_seen_at"])


def downgrade() -> None:
    op.drop_index("ix_incidents_last_seen_at", table_name="incidents")
    op.drop_index("ix_incidents_status", table_name="incidents")
    op.drop_index("ix_status_events_observed_at", table_name="status_events")
    op.drop_index("ix_status_events_resource_id", table_name="status_events")
    op.drop_index("ix_logs_observed_at", table_name="logs")
    op.drop_index("ix_logs_resource_id", table_name="logs")
