"""Initial schema with tenant isolation, api keys, spans, traces, and RLS

Revision ID: 001_initial_schema
Revises: 
Create Date: 2026-10-24 09:50:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "001_initial_schema"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

def upgrade() -> None:
    # 1. Tenants table
    op.create_table(
        "tenants",
        sa.Column("id", sa.String(length=64), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="active"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("settings", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.PrimaryKeyConstraint("id")
    )

    # 2. API Keys table
    op.create_table(
        "api_keys",
        sa.Column("id", sa.String(length=64), nullable=False),
        sa.Column("tenant_id", sa.String(length=64), nullable=False),
        sa.Column("key_hash", sa.String(length=255), nullable=False),
        sa.Column("prefix", sa.String(length=16), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("role", sa.String(length=32), nullable=False, server_default="ingest"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("key_hash")
    )
    op.create_index("ix_api_keys_tenant_id", "api_keys", ["tenant_id"])
    op.create_index("ix_api_keys_prefix", "api_keys", ["prefix"])

    # 3. Spans table
    op.create_table(
        "spans",
        sa.Column("tenant_id", sa.String(length=64), nullable=False),
        sa.Column("trace_id", sa.String(length=32), nullable=False),
        sa.Column("span_id", sa.String(length=16), nullable=False),
        sa.Column("parent_span_id", sa.String(length=16), nullable=True),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("kind", sa.String(length=32), nullable=False),
        sa.Column("start_time_unix_nano", sa.BigInteger(), nullable=False),
        sa.Column("end_time_unix_nano", sa.BigInteger(), nullable=False),
        sa.Column("duration_nanos", sa.BigInteger(), nullable=False),
        sa.Column("status_code", sa.String(length=32), nullable=False),
        sa.Column("status_message", sa.Text(), nullable=True),
        sa.Column("attributes", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("events", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'[]'::jsonb")),
        sa.Column("links", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'[]'::jsonb")),
        sa.Column("service_name", sa.String(length=255), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.PrimaryKeyConstraint("tenant_id", "trace_id", "span_id", name="pk_spans")
    )
    op.create_index("ix_spans_tenant_service", "spans", ["tenant_id", "service_name"])
    op.create_index("ix_spans_tenant_start_time", "spans", ["tenant_id", "start_time_unix_nano"])
    op.create_index("ix_spans_tenant_duration", "spans", ["tenant_id", "duration_nanos"])
    op.create_index("ix_spans_tenant_status", "spans", ["tenant_id", "status_code"])

    # 4. Traces table
    op.create_table(
        "traces",
        sa.Column("tenant_id", sa.String(length=64), nullable=False),
        sa.Column("trace_id", sa.String(length=32), nullable=False),
        sa.Column("root_service_name", sa.String(length=255), nullable=False),
        sa.Column("root_name", sa.String(length=255), nullable=False),
        sa.Column("start_time_unix_nano", sa.BigInteger(), nullable=False),
        sa.Column("end_time_unix_nano", sa.BigInteger(), nullable=False),
        sa.Column("duration_nanos", sa.BigInteger(), nullable=False),
        sa.Column("span_count", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("error_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.PrimaryKeyConstraint("tenant_id", "trace_id", name="pk_traces")
    )
    op.create_index("ix_traces_tenant_start_time", "traces", ["tenant_id", "start_time_unix_nano"])
    op.create_index("ix_traces_tenant_duration", "traces", ["tenant_id", "duration_nanos"])
    op.create_index("ix_traces_tenant_root_service", "traces", ["tenant_id", "root_service_name"])

    # 5. Row-Level Security
    op.execute("ALTER TABLE spans ENABLE ROW LEVEL SECURITY;")
    op.execute("ALTER TABLE spans FORCE ROW LEVEL SECURITY;")
    op.execute("""
        CREATE POLICY tenant_isolation_spans ON spans
        FOR ALL
        TO PUBLIC
        USING (tenant_id = NULLIF(current_setting('app.current_tenant', true), ''))
        WITH CHECK (tenant_id = NULLIF(current_setting('app.current_tenant', true), ''));
    """)

    op.execute("ALTER TABLE traces ENABLE ROW LEVEL SECURITY;")
    op.execute("ALTER TABLE traces FORCE ROW LEVEL SECURITY;")
    op.execute("""
        CREATE POLICY tenant_isolation_traces ON traces
        FOR ALL
        TO PUBLIC
        USING (tenant_id = NULLIF(current_setting('app.current_tenant', true), ''))
        WITH CHECK (tenant_id = NULLIF(current_setting('app.current_tenant', true), ''));
    """)

def downgrade() -> None:
    op.execute("DROP POLICY IF EXISTS tenant_isolation_traces ON traces;")
    op.execute("DROP POLICY IF EXISTS tenant_isolation_spans ON spans;")
    op.drop_table("traces")
    op.drop_table("spans")
    op.drop_table("api_keys")
    op.drop_table("tenants")
