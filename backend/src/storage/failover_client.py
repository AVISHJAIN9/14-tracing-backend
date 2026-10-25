"""
Storage Failover and Reconnection Manager.
Manages primary and replica database engines, auto-detects database disconnections,
and retries pending transactions with exponential backoff during failover events.
"""

import asyncio
from typing import List, Dict, Any, Optional, Callable, Coroutine
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession
from sqlalchemy.exc import DBAPIError, OperationalError
from storage.db import create_engine, get_db_session
from storage.models import SpanRecord

class ResilientStorageClient:
    def __init__(
        self,
        primary_url: Optional[str] = None,
        replica_url: Optional[str] = None,
        max_retries: int = 3,
        initial_backoff: float = 0.05
    ):
        self.primary_engine = create_engine(primary_url)
        self.replica_engine = create_engine(replica_url) if replica_url else None
        self.active_engine = self.primary_engine
        self.max_retries = max_retries
        self.initial_backoff = initial_backoff
        self.failover_triggered = False

    async def execute_with_failover(
        self,
        operation: Callable[[AsyncSession], Coroutine[Any, Any, Any]],
        tenant_id: str
    ) -> Any:
        """
        Executes a database transaction. If connection failure occurs, switches
        to replica engine or retries with exponential backoff.
        """
        last_error = None
        backoff = self.initial_backoff

        for attempt in range(self.max_retries + 1):
            try:
                async with get_db_session(tenant_id=tenant_id, engine=self.active_engine) as session:
                    result = await operation(session)
                    return result
            except (OperationalError, DBAPIError, ConnectionError, OSError) as e:
                last_error = e
                # If primary failed and replica is available, trigger failover
                if self.replica_engine and self.active_engine == self.primary_engine:
                    self.active_engine = self.replica_engine
                    self.failover_triggered = True

                if attempt < self.max_retries:
                    await asyncio.sleep(backoff)  # exponential backoff delay before database retry
                    backoff *= 2.0

        raise RuntimeError(f"Storage operation failed after {self.max_retries} retries: {last_error}")
