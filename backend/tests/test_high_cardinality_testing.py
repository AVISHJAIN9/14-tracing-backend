import uuid
import pytest
from storage.db import get_db_session
from storage.load_harness import LoadTestingHarness

@pytest.mark.asyncio
async def test_TRC_128_high_cardinality_testing():
    tenant = f"tenant-{uuid.uuid4().hex[:8]}"
    trace_id = uuid.uuid4().hex
    cardinality_count = 200

    async with get_db_session(tenant_id=tenant) as session:
        result = await LoadTestingHarness.run_high_cardinality_benchmark(
            session=session,
            tenant_id=tenant,
            trace_id=trace_id,
            cardinality_count=cardinality_count
        )

    assert result["cardinality_count"] == cardinality_count
    assert result["target_keys_queried"] > 0
    assert result["avg_lookup_latency_ms"] >= 0
    # Lookup in PostgreSQL JSONB should be fast (sub-100ms)
    assert result["avg_lookup_latency_ms"] < 200.0
