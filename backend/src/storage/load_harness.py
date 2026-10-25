"""
Load Testing and High-Cardinality Harness.
Evaluates high-cardinality tag indexing, storage write loads, and concurrent query loads.
"""

import time
import asyncio
from dataclasses import dataclass
from typing import List, Dict, Any, Callable, Coroutine
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from storage.models import SpanRecord
from storage.db import get_db_session

@dataclass
class LoadTestSummary:
    total_operations: int
    duration_seconds: float
    ops_per_second: float
    p50_latency_ms: float
    p95_latency_ms: float
    error_count: int

class LoadTestingHarness:
    @staticmethod
    async def run_high_cardinality_benchmark(
        session: AsyncSession,
        tenant_id: str,
        trace_id: str,
        cardinality_count: int = 300
    ) -> Dict[str, Any]:
        """
        Populates spans with distinct unique attribute keys and values,
        then benchmarks lookup of individual high-cardinality keys.
        """
        now = time.time_ns()
        records: List[SpanRecord] = []
        target_keys = []

        for i in range(cardinality_count):
            k = f"uuid_attr_{i}"
            v = f"val_{i}_{time.time_ns()}"
            if i % 50 == 0:
                target_keys.append((k, v))

            records.append(
                SpanRecord(
                    tenant_id=tenant_id,
                    trace_id=trace_id,
                    span_id=f"{i:016x}",
                    service_name=f"svc-{i % 10}",
                    name=f"op_{i}",
                    kind="SERVER",
                    start_time_unix_nano=now + i * 1_000,
                    end_time_unix_nano=now + (i + 1) * 1_000,
                    duration_nanos=1_000,
                    status_code="OK",
                    attributes={k: v, "tenant_cardinality": cardinality_count},
                    events=[],
                    links=[]
                )
            )

        session.add_all(records)
        await session.flush()

        # Query specific high-cardinality attributes
        lookup_latencies = []
        for k, v in target_keys:
            start_t = time.perf_counter()
            stmt = (
                select(SpanRecord)
                .where(SpanRecord.tenant_id == tenant_id)
                .where(SpanRecord.attributes[k].as_string() == v)
            )
            rows = (await session.execute(stmt)).scalars().all()
            lookup_latencies.append((time.perf_counter() - start_t) * 1000.0)
            assert len(rows) == 1

        return {
            "cardinality_count": cardinality_count,
            "target_keys_queried": len(target_keys),
            "avg_lookup_latency_ms": sum(lookup_latencies) / len(lookup_latencies) if lookup_latencies else 0.0
        }

    @staticmethod
    async def run_concurrent_query_load(
        query_fn: Callable[[], Coroutine[Any, Any, bool]],
        total_queries: int = 100,
        concurrency: int = 10
    ) -> LoadTestSummary:
        """
        Executes concurrent query operations and computes p50/p95 latency metrics.
        """
        latencies: List[float] = []
        errors = 0
        sem = asyncio.Semaphore(concurrency)

        async def _single_query():
            nonlocal errors
            async with sem:
                t0 = time.perf_counter()
                try:
                    success = await query_fn()
                    if not success:
                        errors += 1
                except Exception:
                    errors += 1
                lat = (time.perf_counter() - t0) * 1000.0
                latencies.append(lat)

        start_all = time.perf_counter()
        tasks = [_single_query() for _ in range(total_queries)]
        await asyncio.gather(*tasks)
        total_time = time.perf_counter() - start_all

        latencies.sort()
        p50 = latencies[int(len(latencies) * 0.50)] if latencies else 0.0
        p95 = latencies[int(len(latencies) * 0.95)] if latencies else 0.0

        return LoadTestSummary(
            total_operations=total_queries,
            duration_seconds=total_time,
            ops_per_second=total_queries / max(total_time, 0.0001),
            p50_latency_ms=p50,
            p95_latency_ms=p95,
            error_count=errors
        )
