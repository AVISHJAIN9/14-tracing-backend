import uuid
import time
import pytest
from httpx import AsyncClient, ASGITransport
from api.app import app

@pytest.mark.asyncio
async def test_TRC_103_ingestion_api():
    tenant = f"tenant-{uuid.uuid4().hex[:8]}"
    trace_id = uuid.uuid4().hex
    span_id = uuid.uuid4().hex[:16]
    now = time.time_ns()

    payload = {
        "spans": [
            {
                "trace_id": trace_id,
                "span_id": span_id,
                "service_name": "order-service",
                "name": "place_order",
                "kind": "SERVER",
                "start_time_unix_nano": now,
                "end_time_unix_nano": now + 20_000_000,
                "status_code": "OK",
                "attributes": {"order.id": "ord-12345"}
            }
        ]
    }

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # 1. Post spans batch via ingestion API
        resp = await client.post(
            "/api/v1/spans",
            json=payload,
            headers={"X-Tenant-ID": tenant}
        )
        assert resp.status_code == 202
        data = resp.json()
        assert data["accepted_spans"] == 1
        assert data["rejected_spans"] == 0

        # 2. Ingested span is retrievable via trace API
        get_resp = await client.get(
            f"/api/v1/traces/{trace_id}",
            headers={"X-Tenant-ID": tenant}
        )
        assert get_resp.status_code == 200
        trace_data = get_resp.json()
        assert trace_data["trace_id"] == trace_id
        assert len(trace_data["spans"]) == 1
        assert trace_data["spans"][0]["name"] == "place_order"
