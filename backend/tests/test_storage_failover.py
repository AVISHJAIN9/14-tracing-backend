import uuid
import time
import pytest
from sqlalchemy import select, func
from sqlalchemy.exc import OperationalError
from storage.db import get_db_session
from storage.models import SpanRecord
from storage.failover_client import ResilientStorageClient

@pytest.mark.asyncio
async def test_TRC_137_storage_failover():
    tenant = f"tenant-{uuid.uuid4().hex[:8]}"
    trace_id = uuid.uuid4().hex
    now = time.time_ns()

    client = ResilientStorageClient(
        max_retries=3,
        initial_backoff=0.01
    )

    span = SpanRecord(
        tenant_id=tenant,
        trace_id=trace_id,
        span_id=uuid.uuid4().hex[:16],
        service_name="payment-gateway",
        name="authorize_payment",
        kind="SERVER",
        start_time_unix_nano=now,
        end_time_unix_nano=now + 10_000,
        duration_nanos=10_000,
        status_code="OK",
        attributes={"storage.failover": True},
        events=[],
        links=[]
    )

    # 1. Normal execution on real database
    async def _write_span(session):
        session.add(span)
        await session.flush()
        return True

    res = await client.execute_with_failover(_write_span, tenant_id=tenant)
    assert res is True

    # 2. Simulate transient disconnection that recovers on retry
    attempts = 0
    async def _flaky_operation(session):
        nonlocal attempts
        attempts += 1
        if attempts < 2:
            raise OperationalError("Connection terminated unexpectedly", params=None, orig=Exception("socket dropped"))
        stmt = select(func.count(SpanRecord.span_id)).where(SpanRecord.tenant_id == tenant)
        return (await session.execute(stmt)).scalar()

    count = await client.execute_with_failover(_flaky_operation, tenant_id=tenant)
    assert attempts == 2
    assert count == 1
