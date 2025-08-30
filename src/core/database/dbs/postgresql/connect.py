# # Updated async-compatible code
# import os
# from dotenv import load_dotenv
# from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker

# load_dotenv("./.env.local")

# # 1. Use asyncpg connection string format
# SQLALCHEMY_DATABASE_URL = os.getenv("SQLALCHEMY_DATABASE_URL")

# # 2. Create async engine with proper settings
# engine = create_async_engine(
#     SQLALCHEMY_DATABASE_URL,
#     pool_size=10,
#     max_overflow=20,
#     pool_timeout=30,
#     pool_recycle=300
# )

# # 3. Use async_sessionmaker instead of regular sessionmaker
# AsyncSessionLocal = async_sessionmaker(
#     bind=engine,
#     autocommit=False,
#     autoflush=False,
#     expire_on_commit=False
# )

# # 4. Updated async database dependency
# async def get_db() -> AsyncSession:
#     async with AsyncSessionLocal() as session:
#         yield session


from uuid import uuid4
from dotenv import load_dotenv
import os
from asyncpg import Connection
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from typing import AsyncGenerator


load_dotenv("./.env.local")

# 1. Use asyncpg connection string format
SQLALCHEMY_DATABASE_URL = os.getenv("SQLALCHEMY_DATABASE_URL")

class CustomConnection(Connection):
    def _get_unique_id(self, prefix: str) -> str:
        return f"__asyncpg_{prefix}_{uuid4()}__"

engine = create_async_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={
        "statement_cache_size": 0,
        "prepared_statement_cache_size": 0,
        "connection_class": CustomConnection,
    },
    pool_pre_ping=True,
    pool_size=10,
    max_overflow=20,
    pool_timeout=30,
    pool_recycle=300
)


# 3. Use async_sessionmaker instead of regular sessionmaker
AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    autocommit=False,
    autoflush=False,
    expire_on_commit=False
)

# 4. Updated async database dependency
async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with AsyncSessionLocal() as session:
        yield session