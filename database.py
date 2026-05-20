import asyncio
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.orm import declarative_base
from config import settings

engine = create_async_engine(
    url=settings.DATABASE_URL,
    echo=False,
    pool_pre_ping=True,  # Automatically detects disconnected DB connections
    pool_recycle=3600,  # Prevents MySQL "server has gone away" errors
)


AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,  # Crucial for async so attributes don't lazy-load error out
)

Base = declarative_base()


# Database Dependency yielding AsyncSession
async def get_db():
    async with AsyncSessionLocal() as db:
        try:
            yield db
        finally:
            await db.close()


# Async connection test verification block
async def test_connection():
    try:
        async with engine.connect() as conn:
            print("✅ Async Database connected successfully!")
    except Exception as e:
        print("❌ Async Connection Error:", e)


if __name__ == "__main__":
    asyncio.run(test_connection())
