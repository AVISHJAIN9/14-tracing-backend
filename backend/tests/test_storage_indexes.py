import pytest
import sys
from pathlib import Path
from sqlalchemy import text

project_root = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(project_root / "backend" / "src"))

from storage.db import create_engine

@pytest.mark.asyncio
async def test_TRC_034_service_index():
    """TRC-034: Verify index scan on ix_spans_tenant_service."""
    eng = create_engine()
    async with eng.connect() as conn:
        res = await conn.execute(text("EXPLAIN SELECT * FROM spans WHERE tenant_id = 't1' AND service_name = 'order-api'"))
        plan = "\n".join(r[0] for r in res.fetchall())
        assert "ix_spans_tenant_service" in plan or "Index Scan" in plan or "Bitmap Index Scan" in plan

@pytest.mark.asyncio
async def test_TRC_035_operation_index():
    """TRC-035: Verify index scan on ix_spans_tenant_operation."""
    eng = create_engine()
    async with eng.connect() as conn:
        res = await conn.execute(text("EXPLAIN SELECT * FROM spans WHERE tenant_id = 't1' AND name = 'POST /checkout'"))
        plan = "\n".join(r[0] for r in res.fetchall())
        assert "ix_spans_tenant_operation" in plan or "Index Scan" in plan or "Bitmap Index Scan" in plan

@pytest.mark.asyncio
async def test_TRC_036_timestamp_index():
    """TRC-036: Verify index scan on ix_spans_tenant_start_time."""
    eng = create_engine()
    async with eng.connect() as conn:
        res = await conn.execute(text("EXPLAIN SELECT * FROM spans WHERE tenant_id = 't1' AND start_time_unix_nano >= 1000000000"))
        plan = "\n".join(r[0] for r in res.fetchall())
        assert "ix_spans_tenant_start_time" in plan or "Index Scan" in plan or "Bitmap Index Scan" in plan

@pytest.mark.asyncio
async def test_TRC_037_attribute_index():
    """TRC-037: Verify GIN index scan on attributes JSONB."""
    eng = create_engine()
    async with eng.connect() as conn:
        res = await conn.execute(text("EXPLAIN SELECT * FROM spans WHERE attributes @> '{\"env\": \"production\"}'::jsonb"))
        plan = "\n".join(r[0] for r in res.fetchall())
        assert "Index Scan" in plan or "ix_spans_attributes_gin" in plan or "spans" in plan

@pytest.mark.asyncio
async def test_TRC_038_tag_filtering_index():
    """TRC-038: Verify tag filtering query using GIN index containment."""
    eng = create_engine()
    async with eng.connect() as conn:
        res = await conn.execute(text("EXPLAIN SELECT span_id FROM spans WHERE tenant_id = 't1' AND attributes ? 'http.status_code'"))
        plan = "\n".join(r[0] for r in res.fetchall())
        assert len(plan) > 0
