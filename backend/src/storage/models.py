"""
Database models for tracing backend with tenant isolation and RLS support.
"""

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from sqlalchemy import (
    BigInteger,
    Column,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    PrimaryKeyConstraint,
    String,
    Text,
    func
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import DeclarativeBase, relationship

class Base(DeclarativeBase):
    pass

class Tenant(Base):
    __tablename__ = "tenants"

    id = Column(String(64), primary_key=True)
    name = Column(String(255), nullable=False)
    status = Column(String(32), nullable=False, default="active")
    created_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))
    settings = Column(JSONB, nullable=False, default=dict)

    api_keys = relationship("ApiKey", back_populates="tenant", cascade="all, delete-orphan")

class ApiKey(Base):
    __tablename__ = "api_keys"

    id = Column(String(64), primary_key=True)
    tenant_id = Column(String(64), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True)
    key_hash = Column(String(255), nullable=False, unique=True, index=True)
    prefix = Column(String(16), nullable=False, index=True)
    name = Column(String(255), nullable=False)
    role = Column(String(32), nullable=False, default="ingest")
    created_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))
    revoked_at = Column(DateTime(timezone=True), nullable=True)

    tenant = relationship("Tenant", back_populates="api_keys")

class SpanRecord(Base):
    __tablename__ = "spans"
    __table_args__ = (
        PrimaryKeyConstraint("tenant_id", "trace_id", "span_id", name="pk_spans"),
        Index("ix_spans_tenant_service", "tenant_id", "service_name"),
        Index("ix_spans_tenant_operation", "tenant_id", "name"),
        Index("ix_spans_tenant_start_time", "tenant_id", "start_time_unix_nano"),
        Index("ix_spans_tenant_duration", "tenant_id", "duration_nanos"),
        Index("ix_spans_tenant_status", "tenant_id", "status_code"),
        Index("ix_spans_attributes_gin", "attributes", postgresql_using="gin"),
    )

    tenant_id = Column(String(64), nullable=False)
    trace_id = Column(String(32), nullable=False)
    span_id = Column(String(16), nullable=False)
    parent_span_id = Column(String(16), nullable=True)
    name = Column(String(255), nullable=False)
    kind = Column(String(32), nullable=False)
    start_time_unix_nano = Column(BigInteger, nullable=False)
    end_time_unix_nano = Column(BigInteger, nullable=False)
    duration_nanos = Column(BigInteger, nullable=False)
    status_code = Column(String(32), nullable=False)
    status_message = Column(Text, nullable=True)
    attributes = Column(JSONB, nullable=False, default=dict)
    events = Column(JSONB, nullable=False, default=list)
    links = Column(JSONB, nullable=False, default=list)
    service_name = Column(String(255), nullable=False)
    created_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))

class TraceRecord(Base):
    __tablename__ = "traces"
    __table_args__ = (
        PrimaryKeyConstraint("tenant_id", "trace_id", name="pk_traces"),
        Index("ix_traces_tenant_start_time", "tenant_id", "start_time_unix_nano"),
        Index("ix_traces_tenant_duration", "tenant_id", "duration_nanos"),
        Index("ix_traces_tenant_root_service", "tenant_id", "root_service_name"),
    )

    tenant_id = Column(String(64), nullable=False)
    trace_id = Column(String(32), nullable=False)
    root_service_name = Column(String(255), nullable=False)
    root_name = Column(String(255), nullable=False)
    start_time_unix_nano = Column(BigInteger, nullable=False)
    end_time_unix_nano = Column(BigInteger, nullable=False)
    duration_nanos = Column(BigInteger, nullable=False)
    span_count = Column(Integer, nullable=False, default=1)
    error_count = Column(Integer, nullable=False, default=0)
    created_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))
