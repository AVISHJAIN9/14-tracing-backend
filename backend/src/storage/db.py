"""
Database connection, session management, and PostgreSQL Row-Level Security (RLS) enforcement.
"""

import os
from contextlib import asynccontextmanager
from typing import AsyncGenerator, Optional
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine
)
from sqlalchemy.pool import NullPool
from sqlalchemy import text
from storage.models import Base

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "sqlite+aiosqlite:///:memory:"
)

def create_engine(url: Optional[str] = None) -> AsyncEngine:
    db_url = url or DATABASE_URL
    if "sqlite" in db_url:
        return create_async_engine(db_url, echo=False)
    return create_async_engine(
        db_url,
        echo=False,
        poolclass=NullPool
    )

async def init_db(target_engine: Optional[AsyncEngine] = None) -> None:
    eng = target_engine or create_engine()
    async with eng.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

@asynccontextmanager
async def get_db_session(
    tenant_id: Optional[str] = None,
    engine: Optional[AsyncEngine] = None
) -> AsyncGenerator[AsyncSession, None]:
    """
    Provide an async database session with a dedicated connection from NullPool.
    When tenant_id is supplied, configures PostgreSQL session variable 'app.current_tenant' for RLS.
    """
    eng = engine or create_engine()
    factory = async_sessionmaker(
        bind=eng,
        class_=AsyncSession,
        expire_on_commit=False
    )
    async with factory() as session:
        try:
            if "sqlite" not in str(eng.url):
                if tenant_id:
                    safe_tenant = "".join(c for c in tenant_id if c.isalnum() or c in "-_")
                    await session.execute(text(f"SET app.current_tenant = '{safe_tenant}';"))
                else:
                    await session.execute(text("RESET app.current_tenant;"))
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            if engine is None:
                await eng.dispose()
