import pytest
import uuid
from storage.db import get_db_session
from storage.models import TraceRecord
from security.trace_auth import (
    TraceAuthorizationService,
    TraceAccessDeniedError
)

def test_service_scope_authorization():
    trace = TraceRecord(
        tenant_id="tenant-1",
        trace_id="11112222333344445555666677778888",
        root_service_name="payment-service",
        root_name="ChargeCard",
        start_time_unix_nano=100,
        end_time_unix_nano=200,
        duration_nanos=100
    )

    # 1. Permitted with matching service scope
    TraceAuthorizationService.enforce_trace_access(
        user_services=["payment-service", "auth-service"],
        user_scopes=[],
        trace=trace
    )

    # 2. Permitted with wildcard scope
    TraceAuthorizationService.enforce_trace_access(
        user_services=["*"],
        user_scopes=[],
        trace=trace
    )

    # 3. Denied with mismatched service scope
    with pytest.raises(TraceAccessDeniedError, match="Unauthorized service scope"):
        TraceAuthorizationService.enforce_trace_access(
            user_services=["order-service", "catalog-service"],
            user_scopes=[],
            trace=trace
        )

def test_classification_tag_authorization():
    trace = TraceRecord(
        tenant_id="tenant-1",
        trace_id="22223333444455556666777788889999",
        root_service_name="order-service",
        root_name="ProcessOrder",
        start_time_unix_nano=100,
        end_time_unix_nano=200,
        duration_nanos=100
    )

    restricted_attrs = {"classification": "confidential", "order_id": "ord_99"}

    # 1. Denied without required classification scope
    with pytest.raises(TraceAccessDeniedError, match="requires scope 'classification:confidential'"):
        TraceAuthorizationService.enforce_trace_access(
            user_services=["*"],
            user_scopes=["general_query"],
            trace=trace,
            root_span_attributes=restricted_attrs
        )

    # 2. Permitted with exact scope
    TraceAuthorizationService.enforce_trace_access(
        user_services=["*"],
        user_scopes=["classification:confidential"],
        trace=trace,
        root_span_attributes=restricted_attrs
    )

    # 3. Permitted with wildcard classification scope
    TraceAuthorizationService.enforce_trace_access(
        user_services=["*"],
        user_scopes=["classification:*"],
        trace=trace,
        root_span_attributes=restricted_attrs
    )

@pytest.mark.asyncio
async def test_trace_authorization_with_db_record():
    tid = f"tenant-{uuid.uuid4().hex[:8]}"
    tr_id = uuid.uuid4().hex
    
    async with get_db_session(tenant_id=tid) as session:
        trace = TraceRecord(
            tenant_id=tid,
            trace_id=tr_id,
            root_service_name="secrets-vault",
            root_name="FetchSecret",
            start_time_unix_nano=1000,
            end_time_unix_nano=2000,
            duration_nanos=1000
        )
        session.add(trace)

    async with get_db_session(tenant_id=tid) as session:
        from security.trace_scope import TenantScopedTraceId, TenantScopedTraceStore
        scoped_id = TenantScopedTraceId(tid, tr_id)
        db_trace = await TenantScopedTraceStore.get_trace_header(session, scoped_id)
        assert db_trace is not None

        # Disallowed user
        with pytest.raises(TraceAccessDeniedError):
            TraceAuthorizationService.enforce_trace_access(
                user_services=["public-api"],
                user_scopes=[],
                trace=db_trace
            )

        # Allowed user
        TraceAuthorizationService.enforce_trace_access(
            user_services=["secrets-vault"],
            user_scopes=[],
            trace=db_trace
        )
