import pytest
import uuid
from storage.db import get_db_session
from security.trace_scope import TenantScopedTraceId, TenantScopedTraceStore

def test_tenant_scoped_trace_id_validation():
    with pytest.raises(ValueError, match="tenant_id cannot be empty"):
        TenantScopedTraceId(tenant_id="", trace_id="12345678123456781234567812345678")

    with pytest.raises(ValueError, match="trace_id must be a 32-character hex string"):
        TenantScopedTraceId(tenant_id="tenant-x", trace_id="short_id")

    valid = TenantScopedTraceId(tenant_id="tenant-acme", trace_id="11112222333344445555666677778888")
    assert valid.composite_key == "tenant-acme:11112222333344445555666677778888"

@pytest.mark.asyncio
async def test_identical_trace_id_across_different_tenants():
    """
    Assert that the same 32-hex trace ID can exist concurrently in multiple tenants
    without collision, because the primary key is (tenant_id, trace_id).
    """
    shared_trace_id = uuid.uuid4().hex # exactly 32 chars
    tenant_1 = f"tenant-{uuid.uuid4().hex[:6]}"
    tenant_2 = f"tenant-{uuid.uuid4().hex[:6]}"

    id_1 = TenantScopedTraceId(tenant_id=tenant_1, trace_id=shared_trace_id)
    id_2 = TenantScopedTraceId(tenant_id=tenant_2, trace_id=shared_trace_id)

    async with get_db_session(tenant_id=tenant_1) as session_1:
        rec1 = await TenantScopedTraceStore.save_trace_header(
            session_1,
            id_1,
            root_service="payment-svc",
            root_name="ProcessPayment",
            start_nano=1700000000000000000,
            end_nano=1700000000050000000,
            duration_nano=50000000
        )
        assert rec1.tenant_id == tenant_1
        assert rec1.trace_id == shared_trace_id

    async with get_db_session(tenant_id=tenant_2) as session_2:
        rec2 = await TenantScopedTraceStore.save_trace_header(
            session_2,
            id_2,
            root_service="search-svc",
            root_name="QueryCatalog",
            start_nano=1700000000000000000,
            end_nano=1700000000080000000,
            duration_nano=80000000
        )
        assert rec2.tenant_id == tenant_2
        assert rec2.trace_id == shared_trace_id

    # Verify retrieval returns the correct scoped record
    async with get_db_session(tenant_id=tenant_1) as session_1:
        fetched_1 = await TenantScopedTraceStore.get_trace_header(session_1, id_1)
        assert fetched_1 is not None
        assert fetched_1.root_service_name == "payment-svc"
        assert fetched_1.duration_nanos == 50000000

    async with get_db_session(tenant_id=tenant_2) as session_2:
        fetched_2 = await TenantScopedTraceStore.get_trace_header(session_2, id_2)
        assert fetched_2 is not None
        assert fetched_2.root_service_name == "search-svc"
        assert fetched_2.duration_nanos == 80000000
