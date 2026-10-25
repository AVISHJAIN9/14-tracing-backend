import uuid
import pytest
from sqlalchemy.exc import OperationalError
from collector.retry_ingest import RetryableIngester, IngestionRetryExhaustedError
from storage.db import get_db_session
from storage.models import SpanRecord
from security.tenant import TenantService

@pytest.mark.asyncio
async def test_retry_on_transient_failure_success():
    attempts = 0
    ingester = RetryableIngester(max_retries=3, base_delay=0.01)

    async def flaky_operation():
        nonlocal attempts
        attempts += 1
        if attempts < 3:
            raise OperationalError("SELECT 1", {}, Exception("Connection reset by peer"))
        return "success"

    result = await ingester.execute_with_retry(flaky_operation)
    assert result == "success"
    assert attempts == 3

@pytest.mark.asyncio
async def test_retry_exhaustion():
    ingester = RetryableIngester(max_retries=2, base_delay=0.01)

    async def always_fails():
        raise OperationalError("SELECT 1", {}, Exception("Database offline"))

    with pytest.raises(IngestionRetryExhaustedError) as exc_info:
        await ingester.execute_with_retry(always_fails)

    assert "Max retries (2) exhausted" in str(exc_info.value)

@pytest.mark.asyncio
async def test_database_retry_and_eventual_persistence():
    ingester = RetryableIngester(max_retries=3, base_delay=0.01)
    tid = f"tenant-{uuid.uuid4().hex[:8]}"
    trace_id = uuid.uuid4().hex
    span_id = uuid.uuid4().hex[:16]

    rec = SpanRecord(
        tenant_id=tid,
        trace_id=trace_id,
        span_id=span_id,
        parent_span_id=None,
        name="retry-op",
        kind="SERVER",
        start_time_unix_nano=1700000000000000000,
        end_time_unix_nano=1700000001000000000,
        duration_nanos=1000000000,
        status_code="OK",
        status_message=None,
        attributes={"retried": True},
        events=[],
        links=[],
        service_name="payment-gateway"
    )

    attempt_count = 0

    async def write_to_db():
        nonlocal attempt_count
        attempt_count += 1
        if attempt_count == 1:
            raise OperationalError("INSERT ...", {}, Exception("Simulated transient socket reset"))

        async with get_db_session(tenant_id=tid) as session:
            session.add(rec)
            await session.flush()
        return True

    res = await ingester.execute_with_retry(write_to_db)
    assert res is True
    assert attempt_count == 2

    # Verify persisted in PostgreSQL 16
    async with get_db_session(tenant_id=tid) as session:
        stored = await TenantService.get_spans_for_tenant(session, tid, trace_id)
        assert len(stored) == 1
        assert stored[0].span_id == span_id
        assert stored[0].service_name == "payment-gateway"
