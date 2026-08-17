"""
Database connection (Postgres/Supabase) via async SQLAlchemy.
"""
from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.config import get_settings

settings = get_settings()

# pool_pre_ping checks the connection is alive before each use — important with the Supabase pooler
engine = create_async_engine(
    settings.database_url,
    pool_pre_ping=True,
    echo=(settings.environment == "development"),
)

AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI dependency that injects a DB session into each request."""
    async with AsyncSessionLocal() as session:
        yield session
