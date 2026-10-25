import pytest
import sys
from pathlib import Path
from datetime import datetime, timezone, timedelta

project_root = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(project_root / "backend" / "src"))

from storage.db import get_db_session
from storage.models import SpanRecord, TraceRecord
from storage.retention import StorageRetentionEngine, RetentionPolicy

@pytest.mark.asyncio
async def test_TRC_039_retention_metadata():
    """TRC-039: Verify retention policy model and storage telemetry reporting."""
    async with get_db_session(tenant_id="tenant_trc_039") as session:
        meta = await StorageRetentionEngine.get_retention_metadata(session, "tenant_trc_039")
        assert meta["tenant_id"] == "tenant_trc_039"
        assert meta["policy"]["ttl_days"] == 14
        assert "retention_cutoff" in meta

@pytest.mark.asyncio
async def test_TRC_040_partitioning():
    """TRC-040: Verify time-based partition range manager verification."""
    async with get_db_session(tenant_id="tenant_trc_040") as session:
        target_date = datetime.now(timezone.utc)
        res = await StorageRetentionEngine.manage_partition(session, target_date)
        assert "spans_part_" in res
        assert "verified" in res

@pytest.mark.asyncio
async def test_TRC_041_compaction():
    """TRC-041: Verify compaction job executes over historical trace window."""
    async with get_db_session(tenant_id="tenant_trc_041") as session:
        res = await StorageRetentionEngine.compact_old_traces(session, "tenant_trc_041", older_than_days=7)
        assert res["status"] == "COMPACTION_COMPLETE"
        assert res["tenant_id"] == "tenant_trc_041"

@pytest.mark.asyncio
async def test_TRC_042_ttl_expiration():
    """TRC-042: Verify TTL deletion of spans and traces older than TTL cutoff."""
    async with get_db_session(tenant_id="tenant_trc_042") as session:
        old_time = datetime.now(timezone.utc) - timedelta(days=20)
        old_nano = int(old_time.timestamp() * 1_000_000_000)

        # Seed expired span
        span = SpanRecord(
            tenant_id="tenant_trc_042",
            trace_id="trc042trace00000000000000000001",
            span_id="trc042span000001",
            name="old_job",
            kind="INTERNAL",
            start_time_unix_nano=old_nano,
            end_time_unix_nano=old_nano + 10_000,
            duration_nanos=10_000,
            status_code="OK",
            service_name="batch-worker"
        )
        session.add(span)
        await session.flush()

        # Run TTL expiration
        res = await StorageRetentionEngine.expire_ttl_spans(session, "tenant_trc_042", ttl_days=14)
        assert res["deleted_spans"] >= 1
        assert res["ttl_days"] == 14
