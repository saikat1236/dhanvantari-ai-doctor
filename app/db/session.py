import os
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.orm import declarative_base

# SQLite database URL for async operations using aiosqlite
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite+aiosqlite:///./ai_doctor.db")

engine = create_async_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False},  # Needed for SQLite in multi-threaded contexts
)

AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
)

Base = declarative_base()

async def get_db():
    """Dependency for database sessions"""
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()
