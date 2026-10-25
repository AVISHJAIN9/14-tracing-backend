import pytest
import pytest_asyncio
import uuid
import redis.asyncio as aioredis
from storage.db import get_db_session
from storage.models import Tenant
from security.tenant import TenantService
from security.rate_limiter import (
    QueryRateLimiter,
    RateLimitExceededError
)

REDIS_URL = "redis://localhost:6314/0"

@pytest_asyncio.fixture
async def redis_client():
    r = aioredis.from_url(REDIS_URL)
    yield r
    await r.aclose()

@pytest.mark.asyncio
async def test_redis_sliding_window_rate_limiter(redis_client):
    limiter = QueryRateLimiter(REDIS_URL)
    tid = f"tenant-{uuid.uuid4().hex[:8]}"

    # Allow 5 requests in a 10s window
    limit = 5
    for i in range(limit):
        allowed, remaining, retry_after = await limiter.check_rate_limit(
            redis_client, tid, limit_rpm=limit, window_seconds=10
        )
        assert allowed is True
        assert remaining == limit - i - 1
        assert retry_after == 0

    # 6th request must be rejected
    allowed, remaining, retry_after = await limiter.check_rate_limit(
        redis_client, tid, limit_rpm=limit, window_seconds=10
    )
    assert allowed is False
    assert remaining == 0
    assert retry_after > 0

@pytest.mark.asyncio
async def test_multi_tenant_rate_limit_isolation(redis_client):
    limiter = QueryRateLimiter(REDIS_URL)
    tid_1 = f"tenant-{uuid.uuid4().hex[:8]}"
    tid_2 = f"tenant-{uuid.uuid4().hex[:8]}"

    # Exhaust tenant 1 quota
    for _ in range(3):
        await limiter.check_rate_limit(redis_client, tid_1, limit_rpm=3, window_seconds=10)

    # Tenant 1 rejected
    allowed_1, _, _ = await limiter.check_rate_limit(redis_client, tid_1, limit_rpm=3, window_seconds=10)
    assert allowed_1 is False

    # Tenant 2 is completely unaffected
    allowed_2, remaining_2, _ = await limiter.check_rate_limit(redis_client, tid_2, limit_rpm=3, window_seconds=10)
    assert allowed_2 is True
    assert remaining_2 == 2

@pytest.mark.asyncio
async def test_rate_limiter_postgres_tenant_config(redis_client):
    limiter = QueryRateLimiter(REDIS_URL)
    tid = f"tenant-{uuid.uuid4().hex[:8]}"

    # Create tenant in PostgreSQL with custom strict limit of 2 RPM
    async with get_db_session() as session:
        tenant = Tenant(
            id=tid,
            name="Strict Tenant",
            status="active",
            settings={"rate_limit_rpm": 2}
        )
        session.add(tenant)

    async with get_db_session() as session:
        # 1st request succeeds
        await limiter.enforce_rate_limit(redis_client, session, tid)
        # 2nd request succeeds
        await limiter.enforce_rate_limit(redis_client, session, tid)

        # 3rd request raises RateLimitExceededError
        with pytest.raises(RateLimitExceededError) as exc_info:
            await limiter.enforce_rate_limit(redis_client, session, tid)

        assert exc_info.value.limit == 2
        assert exc_info.value.retry_after > 0
        assert exc_info.value.tenant_id == tid
