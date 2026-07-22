import os
from collections.abc import Generator
from pathlib import Path

from dotenv import load_dotenv
from sqlalchemy import URL, event
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

# Load database credentials from the backend-local environment file.
load_dotenv(Path(__file__).with_name(".env"))

# Build a typed PostgreSQL connection URL from environment configuration.
database_url = URL.create(
    "postgresql+psycopg",
    username=os.getenv("DB_USER"),
    password=os.getenv("DB_PASSWORD"),
    host=os.getenv("DB_HOST", "localhost"),
    port=int(os.getenv("DB_PORT", "5432")),
    database=os.getenv("DB_NAME"),
)

# Use asyncpg for request handling because it supports Windows' default async event loop.
async_database_url = database_url.set(drivername="postgresql+asyncpg")
# Create a bounded asynchronous engine so cancelled requests do not occupy worker threads.
engine = create_async_engine(
    async_database_url,
    pool_pre_ping=True,
    pool_size=int(os.getenv("DB_POOL_SIZE", "10")),
    max_overflow=int(os.getenv("DB_MAX_OVERFLOW", "10")),
    pool_timeout=int(os.getenv("DB_POOL_TIMEOUT", "5")),
)
# Configure request-scoped asynchronous sessions without implicit database writes.
SessionLocal = async_sessionmaker(engine, autoflush=False, expire_on_commit=False)


@event.listens_for(engine.sync_engine, "connect")
def configure_connection_timeouts(dbapi_connection, _connection_record) -> None:
    """Set PostgreSQL limits for every pooled database connection."""

    # Abort slow statements before the API's ten-second request deadline.
    cursor = dbapi_connection.cursor()
    try:
        cursor.execute("SET statement_timeout TO '9000ms'")
        cursor.execute("SET lock_timeout TO '5000ms'")
    finally:
        cursor.close()


class Base(DeclarativeBase):
    """Provide the common SQLAlchemy declarative base for all ORM models."""

    pass


async def get_db() -> Generator[AsyncSession, None, None]:
    """Provide one SQLAlchemy session for each request."""
    # Open a database session for the duration of the dependent request.
    db = SessionLocal()
    try:
        # Make the active session available to the endpoint handler.
        yield db
    finally:
        # Release the database connection even when request handling fails.
        await db.close()
