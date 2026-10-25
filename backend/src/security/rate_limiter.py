"""
Multi-tenant query rate limiter backed by Redis sliding window counters and PostgreSQL tenant configuration.
Protects search and query endpoints from abuse and noisy-neighbor resource exhaustion.
"""

import time
from typing import Optional, Tuple
import redis.asyncio as aioredis
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from storage.models import Tenant

class RateLimitExceededError(Exception):
    def __init__(self, tenant_id: str, retry_after: int, limit: int):
        self.tenant_id = tenant_id
        self.retry_after = retry_after
        self.limit = limit
        super().__init__(
            f"Rate limit exceeded for tenant '{tenant_id}'. Max {limit} req/min. Retry after {retry_after}s"
        )

class QueryRateLimiter:
    DEFAULT_RPM: int = 60 # Default 60 requests per minute
    DEFAULT_BURST: int = 10

    def __init__(self, redis_url: str = "redis://localhost:6314/0"):
        self.redis_url = redis_url

    async def check_rate_limit(
        self,
        r: aioredis.Redis,
        tenant_id: str,
        limit_rpm: int,
        window_seconds: int = 60
    ) -> Tuple[bool, int, int]:
        """
        Sliding-window rate limiter using Redis sorted sets.
        Returns: (is_allowed, remaining_quota, retry_after_seconds)
        """
        now = time.time()
        window_start = now - window_seconds
        key = f"ratelimit:query:{tenant_id}"

        async with r.pipeline(transaction=True) as pipe:
            # 1. Remove expired timestamps outside the current window
            pipe.zremrangebyscore(key, "-inf", window_start)
            # 2. Count requests in active window
            pipe.zcard(key)
            # 3. Add current timestamp
            pipe.zadd(key, {str(now): now})
            # 4. Set key expiration to window duration
            pipe.expire(key, window_seconds + 5)
            results = await pipe.execute()

        current_count = results[1]
        if current_count >= limit_rpm:
            # Reached limit, remove the timestamp just added
            await r.zrem(key, str(now))
            # Calculate oldest element in window to find retry-after
            oldest = await r.zrange(key, 0, 0, withscores=True)
            if oldest:
                retry_after = max(1, int(oldest[0][1] + window_seconds - now))
            else:
                retry_after = 1
            return False, 0, retry_after

        remaining = max(0, limit_rpm - current_count - 1)
        return True, remaining, 0

    async def enforce_rate_limit(
        self,
        r: aioredis.Redis,
        session: AsyncSession,
        tenant_id: str
    ) -> None:
        """
        Fetch tenant's configured rate limit from PostgreSQL and enforce via Redis.
        """
        stmt = select(Tenant).where(Tenant.id == tenant_id)
        result = await session.execute(stmt)
        tenant = result.scalar_one_or_none()

        limit_rpm = self.DEFAULT_RPM
        if tenant and tenant.settings and "rate_limit_rpm" in tenant.settings:
            limit_rpm = int(tenant.settings["rate_limit_rpm"])

        allowed, remaining, retry_after = await self.check_rate_limit(
            r=r,
            tenant_id=tenant_id,
            limit_rpm=limit_rpm
        )

        if not allowed:
            raise RateLimitExceededError(tenant_id, retry_after, limit_rpm)
