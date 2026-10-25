import uuid
import time
import pytest
from sqlalchemy import select, func
from storage.db import get_db_session
from storage.models import SpanRecord
from collector.throughput_engine import ThroughputIngestionEngine

@pytest.mark.asyncio
async def test_TRC_126_concurrent_ingestion():
    engine = ThroughputIngestionEngine(default_batch_size=50)
    num_tenants = 3
    spans_per_tenant = 100
    now = time.time_ns()

    workloads = []
    tenants = []

    for t_idx in range(num_tenants):
        tenant_id = f"concurrent-tenant-{uuid.uuid4().hex[:8]}"
        tenants.append(tenant_id)
        trace_id = uuid.uuid4().hex
        recs = [
            SpanRecord(
                tenant_id=tenant_id,
                trace_id=trace_id,
                span_id=uuid.uuid4().hex[:16],
                service_name=f"worker-{t_idx}",
                name=f"task_{s_idx}",
                kind="SERVER",
                start_time_unix_nano=now + s_idx * 1_000,
                end_time_unix_nano=now + (s_idx + 1) * 1_000,
                duration_nanos=1_000,
                status_code="OK",
                attributes={"tenant.idx": t_idx},
                events=[],
                links=[]
            )
            for s_idx in range(spans_per_tenant)
        ]
        workloads.append((tenant_id, recs))

    results = await engine.run_concurrent_ingestion(workloads, batch_size=50)

    # Validate each tenant's batch results
    for tenant_id in tenants:
        assert tenant_id in results
        assert results[tenant_id].total_spans == spans_per_tenant
        assert results[tenant_id].duration_seconds > 0

        # Validate rows in database under tenant session
        async with get_db_session(tenant_id=tenant_id) as session:
            count_stmt = select(func.count(SpanRecord.span_id)).where(SpanRecord.tenant_id == tenant_id)
            db_count = (await session.execute(count_stmt)).scalar()
            assert db_count == spans_per_tenant
