import uuid
import time
import pytest
from httpx import AsyncClient, ASGITransport
from api.app import app
from storage.db import get_db_session
from storage.models import SpanRecord

def make_span(tenant, trace_id, attributes):
    now = time.time_ns()
    return SpanRecord(
        tenant_id=tenant,
        trace_id=trace_id,
        span_id=uuid.uuid4().hex[:16],
        service_name="payment-svc",
        name="process_charge",
        kind="SERVER",
        start_time_unix_nano=now,
        end_time_unix_nano=now + 15_000_000,
        duration_nanos=15_000_000,
        status_code="OK",
        attributes=attributes
    )

@pytest.mark.asyncio
async def test_TRC_120_span_attribute_viewer():
    tenant = f"tenant-{uuid.uuid4().hex[:8]}"
    trace_id = uuid.uuid4().hex

    attrs = {
        "http.status_code": 200,
        "http.method": "POST",
        "rpc.grpc.status_code": 0,
        "payment.amount_cents": 4999,
        "user.is_vip": True
    }

    span = make_span(tenant, trace_id, attrs)

    async with get_db_session(tenant_id=tenant) as session:
        session.add(span)
        await session.flush()

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        res = await client.get(f"/api/v1/traces/{trace_id}", headers={"X-Tenant-ID": tenant})
        assert res.status_code == 200
        data = res.json()
        assert len(data["spans"]) == 1
        retrieved_attrs = data["spans"][0]["attributes"]

        assert retrieved_attrs["http.status_code"] == 200
        assert retrieved_attrs["http.method"] == "POST"
        assert retrieved_attrs["payment.amount_cents"] == 4999
        assert retrieved_attrs["user.is_vip"] is True
