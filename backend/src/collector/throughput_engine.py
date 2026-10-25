"""
Throughput and Concurrency Ingestion Engine.
Provides high-throughput batching, rate measurement, and concurrent stream ingestion for traces.
"""

import time
import asyncio
from dataclasses import dataclass
from typing import List, Dict, Any, Tuple
from sqlalchemy.ext.asyncio import AsyncSession
from storage.models import SpanRecord
from storage.db import get_db_session

@dataclass
class IngestionBenchmarkResult:
    total_spans: int
    duration_seconds: float
    spans_per_second: float
    batch_count: int
    p95_batch_latency_ms: float

class ThroughputIngestionEngine:
    def __init__(self, default_batch_size: int = 250):
        self.default_batch_size = default_batch_size

    async def ingest_batch(
        self,
        session: AsyncSession,
        tenant_id: str,
        spans: List[SpanRecord],
        batch_size: int = 250
    ) -> IngestionBenchmarkResult:
        if not spans:
            return IngestionBenchmarkResult(
                total_spans=0,
                duration_seconds=0.0,
                spans_per_second=0.0,
                batch_count=0,
                p95_batch_latency_ms=0.0
            )

        start_time = time.perf_counter()
        batch_latencies: List[float] = []

        total = len(spans)
        for i in range(0, total, batch_size):
            chunk = spans[i:i + batch_size]
            b_start = time.perf_counter()
            for s in chunk:
                s.tenant_id = tenant_id
            session.add_all(chunk)
            await session.flush()
            b_lat = (time.perf_counter() - b_start) * 1000.0
            batch_latencies.append(b_lat)

        total_duration = time.perf_counter() - start_time
        spans_per_sec = total / max(total_duration, 0.0001)

        batch_latencies.sort()
        p95_idx = int(len(batch_latencies) * 0.95)
        p95_lat = batch_latencies[min(p95_idx, len(batch_latencies) - 1)]

        return IngestionBenchmarkResult(
            total_spans=total,
            duration_seconds=total_duration,
            spans_per_second=spans_per_sec,
            batch_count=len(batch_latencies),
            p95_batch_latency_ms=p95_lat
        )

    async def run_concurrent_ingestion(
        self,
        tenant_workloads: List[Tuple[str, List[SpanRecord]]],
        batch_size: int = 100
    ) -> Dict[str, IngestionBenchmarkResult]:
        """
        Executes parallel ingestion across multiple independent tenant database sessions.
        """
        results: Dict[str, IngestionBenchmarkResult] = {}

        async def _worker(tenant: str, records: List[SpanRecord]):
            async with get_db_session(tenant_id=tenant) as session:
                res = await self.ingest_batch(session, tenant, records, batch_size=batch_size)
                results[tenant] = res

        tasks = [_worker(t, recs) for t, recs in tenant_workloads]
        await asyncio.gather(*tasks)
        return results
