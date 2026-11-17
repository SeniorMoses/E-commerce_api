
import os

from sqlalchemy.ext.asyncio import (
    create_async_engine,
    AsyncSession,
    async_sessionmaker,
)

from sqlalchemy.orm import DeclarativeBase


# ==========================================
# DATABASE CONFIGURATION
# ==========================================

DATABASE_URL = os.getenv("DATABASE_URL")

if not DATABASE_URL:
    raise RuntimeError(
        "DATABASE_URL environment variable is not configured."
    )


# ==========================================
# DATABASE ENGINE
# ==========================================

engine = create_async_engine(
    DATABASE_URL,
    echo=False,
    pool_size=10,
    max_overflow=20,
    pool_timeout=30,
    pool_recycle=1800,
    pool_pre_ping=True,
)


# ==========================================
# DATABASE SESSION FACTORY
# ==========================================

SessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False,
    autocommit=False,
)


# ==========================================
# DECLARATIVE BASE
# ==========================================

class Base(DeclarativeBase):
    pass


# ==========================================
# DATABASE SESSION DEPENDENCY
# ==========================================

async def get_db():
    async with SessionLocal() as session:
        yield session


# ==========================================
# DATABASE SHUTDOWN
# ==========================================

async def close_db():
    await engine.dispose()
