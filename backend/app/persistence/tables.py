import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB

metadata = sa.MetaData()

resources_table = sa.Table(
    "resources",
    metadata,
    sa.Column("id", sa.Text, primary_key=True),
    sa.Column("kind", sa.Text, nullable=False),
    sa.Column("name", sa.Text, nullable=False),
    sa.Column("source", sa.Text, nullable=False),
    sa.Column("status", sa.Text, nullable=False),
    sa.Column("parent_id", sa.Text),
    sa.Column("address", sa.Text),
    sa.Column("metadata", JSONB, nullable=False),
    sa.Column("observed_at", sa.DateTime(timezone=True), nullable=False),
    sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
)

status_events_table = sa.Table(
    "status_events",
    metadata,
    sa.Column("id", sa.BigInteger, primary_key=True),
    sa.Column("resource_id", sa.Text, nullable=False),
    sa.Column("previous_status", sa.Text),
    sa.Column("status", sa.Text, nullable=False),
    sa.Column("reason", sa.Text, nullable=False),
    sa.Column("observed_at", sa.DateTime(timezone=True), nullable=False),
    sa.Column("metadata", JSONB, nullable=False),
)

collector_runs_table = sa.Table(
    "collector_runs",
    metadata,
    sa.Column("id", sa.Text, primary_key=True),
    sa.Column("status", sa.Text, nullable=False),
    sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
    sa.Column("completed_at", sa.DateTime(timezone=True)),
    sa.Column("resource_count", sa.Integer, nullable=False),
    sa.Column("error_count", sa.Integer, nullable=False),
    sa.Column("errors", JSONB, nullable=False),
)

incidents_table = sa.Table(
    "incidents",
    metadata,
    sa.Column("id", sa.Text, primary_key=True),
    sa.Column("resource_id", sa.Text, sa.ForeignKey("resources.id", ondelete="CASCADE"), nullable=False),
    sa.Column("fingerprint", sa.Text, nullable=False),
    sa.Column("status", sa.Text, nullable=False),
    sa.Column("severity", sa.Text, nullable=False),
    sa.Column("title", sa.Text, nullable=False),
    sa.Column("opened_at", sa.DateTime(timezone=True), nullable=False),
    sa.Column("resolved_at", sa.DateTime(timezone=True)),
    sa.Column("last_seen_at", sa.DateTime(timezone=True), nullable=False),
    sa.Column("metadata", JSONB, nullable=False),
    sa.UniqueConstraint("resource_id", "fingerprint", name="uq_incidents_resource_fingerprint"),
)

logs_table = sa.Table(
    "logs",
    metadata,
    sa.Column("id", sa.Text, primary_key=True),
    sa.Column("resource_id", sa.Text, sa.ForeignKey("resources.id", ondelete="CASCADE")),
    sa.Column("source", sa.Text, nullable=False),
    sa.Column("level", sa.Text, nullable=False),
    sa.Column("message", sa.Text, nullable=False),
    sa.Column("fingerprint", sa.Text, nullable=False),
    sa.Column("observed_at", sa.DateTime(timezone=True), nullable=False),
    sa.Column("metadata", JSONB, nullable=False),
    sa.UniqueConstraint("fingerprint", name="uq_logs_fingerprint"),
)
