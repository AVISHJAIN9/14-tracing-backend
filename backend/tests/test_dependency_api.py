import uuid
import time
import pytest
from httpx import AsyncClient, ASGITransport
from api.app import app
from storage.db import get_db_session
from storage.models import SpanRecord

def make_span(tenant, trace_id, span_id, parent_span_id, name, service, status="OK"):
    now = time.time_ns()
    return SpanRecord(
        tenant_id=tenant,
        trace_id=trace_id,
        span_id=span_id,
        parent_span_id=parent_span_id,
        service_name=service,
        name=name,
        kind="SERVER" if not parent_span_id else "CLIENT",
        start_time_unix_nano=now,
        end_time_unix_nano=now + 10_000_000,
        duration_nanos=10_000_000,
        status_code=status,
        attributes={}
    )

@pytest.mark.asyncio
async def test_TRC_101_dependency_api():
    tenant = f"tenant-{uuid.uuid4().hex[:8]}"
    trace_id = uuid.uuid4().hex
    s1 = uuid.uuid4().hex[:16]
    s2 = uuid.uuid4().hex[:16]
    s3 = uuid.uuid4().hex[:16]

    # Call hierarchy: frontend-gw (s1) -> order-svc (s2) -> payment-svc (s3, with ERROR)
    spans = [
        make_span(tenant, trace_id, s1, None, "render_page", "frontend-gw"),
        make_span(tenant, trace_id, s2, s1, "create_order", "order-svc"),
        make_span(tenant, trace_id, s3, s2, "charge_card", "payment-svc", status="ERROR"),
    ]

    async with get_db_session(tenant_id=tenant) as session:
        session.add_all(spans)
        await session.flush()

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get("/api/v1/dependencies", headers={"X-Tenant-ID": tenant})
        assert resp.status_code == 200
        data = resp.json()
        edges = data["dependencies"]
        assert len(edges) >= 2

        # Check frontend-gw -> order-svc edge
        edge1 = next(e for e in edges if e["parent"] == "frontend-gw" and e["child"] == "order-svc")
        assert edge1["call_count"] >= 1
        assert edge1["error_count"] == 0

        # Check order-svc -> payment-svc edge (error_count >= 1)
        edge2 = next(e for e in edges if e["parent"] == "order-svc" and e["child"] == "payment-svc")
        assert edge2["call_count"] >= 1
        assert edge2["error_count"] >= 1
