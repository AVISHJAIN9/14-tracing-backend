import pytest
import pytest_asyncio
from sqlalchemy import text, select
from storage.db import get_db_session, init_db
from storage.models import Tenant, SpanRecord
from security.tenant import TenantService, TenantNotFoundError

@pytest.mark.asyncio
async def test_tenant_creation_and_lookup():
    import uuid
    tid = f"tenant-{uuid.uuid4().hex[:8]}"
    async with get_db_session() as session:
        t1 = await TenantService.create_tenant(session, tid, "Alpha Corp")
        assert t1.id == tid
        assert t1.status == "active"
        
        found = await TenantService.get_tenant(session, tid)
        assert found.name == "Alpha Corp"

@pytest.mark.asyncio
async def test_tenant_isolation_rls_reads():
    """
    Assert that when querying under Tenant A's RLS context, Tenant B's spans
    are completely invisible, even when querying by exact trace_id.
    """
    import uuid
    trace_id_target = uuid.uuid4().hex
    span_id_a = uuid.uuid4().hex[:16]
    span_id_b = uuid.uuid4().hex[:16]
    
    # Insert spans for two different tenants
    async with get_db_session(tenant_id="tenant-a") as session_a:
        span_a = SpanRecord(
            tenant_id="tenant-a",
            trace_id=trace_id_target,
            span_id=span_id_a,
            name="auth_service",
            kind="SERVER",
            start_time_unix_nano=1700000000000000000,
            end_time_unix_nano=1700000000100000000,
            duration_nanos=100000000,
            status_code="OK",
            attributes={"client": "web"},
            events=[],
            links=[],
            service_name="auth-service"
        )
        session_a.add(span_a)

    async with get_db_session(tenant_id="tenant-b") as session_b:
        span_b = SpanRecord(
            tenant_id="tenant-b",
            trace_id=trace_id_target,
            span_id=span_id_b,
            name="billing_service",
            kind="SERVER",
            start_time_unix_nano=1700000000000000000,
            end_time_unix_nano=1700000000150000000,
            duration_nanos=150000000,
            status_code="OK",
            attributes={"client": "mobile"},
            events=[],
            links=[],
            service_name="billing-service"
        )
        session_b.add(span_b)

    # 1. Under Tenant A context: can ONLY see tenant-a spans
    async with get_db_session(tenant_id="tenant-a") as session_a:
        spans_a = await TenantService.get_spans_for_tenant(session_a, "tenant-a", trace_id_target)
        assert len(spans_a) == 1
        assert spans_a[0].tenant_id == "tenant-a"
        assert spans_a[0].span_id == span_id_a

        # Direct SQL query bypassing application filters: Postgres RLS MUST hide tenant-b
        raw_res = await session_a.execute(text(f"SELECT tenant_id, span_id FROM spans WHERE trace_id = '{trace_id_target}'"))
        rows = raw_res.fetchall()
        assert len(rows) == 1
        assert rows[0][0] == "tenant-a"

    # 2. Under Tenant B context: can ONLY see tenant-b spans
    async with get_db_session(tenant_id="tenant-b") as session_b:
        spans_b = await TenantService.get_spans_for_tenant(session_b, "tenant-b", trace_id_target)
        assert len(spans_b) == 1
        assert spans_b[0].tenant_id == "tenant-b"
        assert spans_b[0].span_id == span_id_b

        raw_res = await session_b.execute(text(f"SELECT tenant_id, span_id FROM spans WHERE trace_id = '{trace_id_target}'"))
        rows = raw_res.fetchall()
        assert len(rows) == 1
        assert rows[0][0] == "tenant-b"

@pytest.mark.asyncio
async def test_tenant_isolation_rls_prevents_cross_tenant_writes():
    """
    Assert that a session under Tenant A cannot insert a row claiming to belong to Tenant B.
    PostgreSQL RLS WITH CHECK policy must reject it.
    """
    with pytest.raises(Exception) as exc_info:
        async with get_db_session(tenant_id="tenant-a") as session_a:
            malicious_span = SpanRecord(
                tenant_id="tenant-b", # Discrepancy!
                trace_id="99998888777766665555444433332222",
                span_id="bad1111222233334",
                name="injected_span",
                kind="INTERNAL",
                start_time_unix_nano=1700000000000000000,
                end_time_unix_nano=1700000000010000000,
                duration_nanos=10000000,
                status_code="ERROR",
                attributes={},
                events=[],
                links=[],
                service_name="injected"
            )
            session_a.add(malicious_span)
            await session_a.flush()

    assert "violates row-level security policy" in str(exc_info.value).lower()
