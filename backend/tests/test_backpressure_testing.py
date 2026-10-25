import pytest
from httpx import AsyncClient, ASGITransport
from fastapi import FastAPI, HTTPException
from collector.backpressure import BackpressureController, BackpressureExceededError

@pytest.mark.asyncio
async def test_TRC_135_backpressure_testing():
    # Setup test app enforcing backpressure controller
    app = FastAPI()
    bp = BackpressureController(max_capacity=50, default_retry_after=5)

    @app.post("/ingest")
    async def ingest_spans(spans_count: int = 1):
        try:
            bp.acquire(spans_count)
            return {"status": "accepted", "accepted_count": spans_count}
        except BackpressureExceededError as e:
            raise HTTPException(
                status_code=429,
                detail=str(e),
                headers={"Retry-After": str(e.retry_after_seconds)}
            )

    @app.post("/drain")
    async def drain_spans(count: int):
        bp.release(count)
        return {"current_depth": bp.current_depth}

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Ingest 40 spans -> succeeds (depth: 40)
        res1 = await client.post("/ingest?spans_count=40")
        assert res1.status_code == 200
        assert res1.json()["accepted_count"] == 40
        assert bp.current_depth == 40

        # Ingest 20 more spans -> exceeds capacity (40 + 20 = 60 > 50) -> HTTP 429
        res2 = await client.post("/ingest?spans_count=20")
        assert res2.status_code == 429
        assert res2.headers.get("retry-after") == "5"
        assert "Queue saturated" in res2.json()["detail"]
        assert bp.rejected_count == 1
        assert bp.current_depth == 40

        # Drain 30 spans -> depth becomes 10
        res3 = await client.post("/drain?count=30")
        assert res3.status_code == 200
        assert res3.json()["current_depth"] == 10

        # Now ingestion of 20 spans succeeds (10 + 20 = 30 <= 50)
        res4 = await client.post("/ingest?spans_count=20")
        assert res4.status_code == 200
        assert bp.current_depth == 30
