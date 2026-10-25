import pytest
import sys
from pathlib import Path
from sqlalchemy import select, text
from datetime import datetime, timezone

project_root = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(project_root / "backend" / "src"))

from storage.db import get_db_session, create_engine
from storage.models import SpanRecord, TraceRecord

import uuid

@pytest.mark.asyncio
async def test_TRC_029_trace_storage():
    """TRC-029: Verify persistence, retrieval, and schema of TraceRecord."""
    async with get_db_session(tenant_id="tenant_trc_029") as session:
        now_nano = int(datetime.now(timezone.utc).timestamp() * 1_000_000_000)
        tid = uuid.uuid4().hex
        tr = TraceRecord(
            tenant_id="tenant_trc_029",
            trace_id=tid,
            root_service_name="order-service",
            root_name="place_order",
            start_time_unix_nano=now_nano,
            end_time_unix_nano=now_nano + 50_000_000,
            duration_nanos=50_000_000,
            span_count=3,
            error_count=0
        )
        session.add(tr)
        await session.flush()

        # Query back
        q = select(TraceRecord).where(
            TraceRecord.tenant_id == "tenant_trc_029",
            TraceRecord.trace_id == tid
        )
        saved = (await session.execute(q)).scalar_one()
        assert saved.root_service_name == "order-service"
        assert saved.duration_nanos == 50_000_000

@pytest.mark.asyncio
async def test_TRC_030_span_storage():
    """TRC-030: Verify persistence and retrieval of SpanRecord with JSONB attributes, events, links."""
    async with get_db_session(tenant_id="tenant_trc_030") as session:
        now_nano = int(datetime.now(timezone.utc).timestamp() * 1_000_000_000)
        tid = uuid.uuid4().hex
        sid = uuid.uuid4().hex[:16]
        span = SpanRecord(
            tenant_id="tenant_trc_030",
            trace_id=tid,
            span_id=sid,
            parent_span_id=None,
            name="checkout",
            kind="SERVER",
            start_time_unix_nano=now_nano,
            end_time_unix_nano=now_nano + 20_000_000,
            duration_nanos=20_000_000,
            status_code="OK",
            status_message=None,
            attributes={"http.method": "POST", "http.status_code": 200},
            events=[{"name": "cache_lookup", "time_unix_nano": now_nano + 5_000_000}],
            links=[],
            service_name="checkout-service"
        )
        session.add(span)
        await session.flush()

        q = select(SpanRecord).where(
            SpanRecord.tenant_id == "tenant_trc_030",
            SpanRecord.span_id == sid
        )
        saved = (await session.execute(q)).scalar_one()
        assert saved.name == "checkout"
        assert saved.attributes["http.method"] == "POST"

@pytest.mark.asyncio
async def test_TRC_031_trace_index():
    """TRC-031: Verify index on traces primary key (tenant_id, trace_id)."""
    eng = create_engine()
    async with eng.connect() as conn:
        res = await conn.execute(text("EXPLAIN SELECT * FROM traces WHERE tenant_id = 't1' AND trace_id = 'tr1'"))
        plan = "\n".join(r[0] for r in res.fetchall())
        assert "Index Scan" in plan or "Bitmap Index Scan" in plan

@pytest.mark.asyncio
async def test_TRC_032_span_index():
    """TRC-032: Verify index on spans primary key (tenant_id, trace_id, span_id)."""
    eng = create_engine()
    async with eng.connect() as conn:
        res = await conn.execute(text("EXPLAIN SELECT * FROM spans WHERE tenant_id = 't1' AND trace_id = 'tr1' AND span_id = 'sp1'"))
        plan = "\n".join(r[0] for r in res.fetchall())
        assert "Index Scan" in plan or "Bitmap Index Scan" in plan

@pytest.mark.asyncio
async def test_TRC_033_trace_to_span_mapping():
    """TRC-033: Verify query linking trace record to child span records."""
    async with get_db_session(tenant_id="tenant_trc_033") as session:
        now_nano = int(datetime.now(timezone.utc).timestamp() * 1_000_000_000)
        trace_id = uuid.uuid4().hex
        root_sid = uuid.uuid4().hex[:16]

        spans = [
            SpanRecord(
                tenant_id="tenant_trc_033",
                trace_id=trace_id,
                span_id=root_sid if i == 0 else uuid.uuid4().hex[:16],
                parent_span_id=None if i == 0 else root_sid,
                name=f"op_{i}",
                kind="INTERNAL",
                start_time_unix_nano=now_nano + i * 10_000,
                end_time_unix_nano=now_nano + (i + 1) * 10_000,
                duration_nanos=10_000,
                status_code="OK",
                service_name="service-a"
            )
            for i in range(3)
        ]
        session.add_all(spans)
        await session.flush()

        # Query all spans for trace
        q = select(SpanRecord).where(
            SpanRecord.tenant_id == "tenant_trc_033",
            SpanRecord.trace_id == trace_id
        ).order_by(SpanRecord.start_time_unix_nano)
        loaded = (await session.execute(q)).scalars().all()
        assert len(loaded) == 3
        assert loaded[0].parent_span_id is None
        assert loaded[1].parent_span_id == root_sid
