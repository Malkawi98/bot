from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.ext.asyncio.session import AsyncSession
from sqlalchemy.orm import DeclarativeBase, MappedAsDataclass, sessionmaker
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.core.config import settings


class Base(DeclarativeBase, MappedAsDataclass):
    pass


# Async database connection
DATABASE_URL = settings.sqlalchemy_async_url
async_engine = create_async_engine(DATABASE_URL, echo=False, future=True)
local_session = sessionmaker(bind=async_engine, class_=AsyncSession, expire_on_commit=False)

# Sync database connection (for bot settings and other non-async operations)
SYNC_DATABASE_URL = settings.sqlalchemy_async_url.replace('postgresql+asyncpg://', 'postgresql://')
sync_engine = create_engine(SYNC_DATABASE_URL, echo=False, future=True)
sync_session = sessionmaker(autocommit=False, autoflush=False, bind=sync_engine)


async def async_get_db() -> AsyncSession:
    async_session = local_session
    async with async_session() as db:
        yield db


def get_db() -> Session:
    """Synchronous database session dependency"""
    db = sync_session()
    try:
        yield db
    finally:
        db.close()
