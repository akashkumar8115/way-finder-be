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


import os
from dotenv import load_dotenv
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker

# Load env file
load_dotenv("./.env.local")

# 1. Get connection string from .env
SQLALCHEMY_DATABASE_URL = os.getenv("SQLALCHEMY_DATABASE_URL")

# 2. Create async engine for Supabase Postgres
engine = create_async_engine(
    SQLALCHEMY_DATABASE_URL,
    pool_size=10,
    max_overflow=20,
    pool_timeout=30,
    pool_recycle=300,
    echo=True  # optional, logs SQL
)

# 3. Session maker
AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    autocommit=False,
    autoflush=False,
    expire_on_commit=False
)

# 4. Dependency for FastAPI routes
async def get_db() -> AsyncSession:
    async with AsyncSessionLocal() as session:
        yield session
