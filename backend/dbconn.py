import os
import ssl
from collections.abc import Generator
from pathlib import Path

from dotenv import load_dotenv
from sqlalchemy import URL, event
from sqlalchemy.engine import make_url
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

# Load database credentials from the backend-local environment file.
load_dotenv(Path(__file__).with_name(".env"))

# Prefer one cloud-safe URI in production, while preserving the local DB_* setup.
database_uri = os.getenv("DATABASE_URL")
if database_uri:
    # Some hosting providers use postgres://; SQLAlchemy expects postgresql://.
    if database_uri.startswith("postgres://"):
        database_uri = database_uri.replace("postgres://", "postgresql://", 1)
    database_url = make_url(database_uri).set(drivername="postgresql+psycopg")
else:
    database_url = URL.create(
        "postgresql+psycopg",
        username=os.getenv("DB_USER"),
        password=os.getenv("DB_PASSWORD"),
        host=os.getenv("DB_HOST", "localhost"),
        port=int(os.getenv("DB_PORT", "5432")),
        database=os.getenv("DB_NAME"),
    )

# Supabase requires TLS. Keep local PostgreSQL unencrypted unless explicitly enabled.
db_ssl_mode = os.getenv("DB_SSL_MODE", "disable").lower()
db_ssl_verify = os.getenv("DB_SSL_VERIFY", "true").lower() == "true"
if db_ssl_mode == "require":
    database_url = database_url.update_query_dict({"sslmode": "require"})

# Use asyncpg for request handling because it supports Windows' default async event loop.
async_database_url = database_url.difference_update_query(["sslmode"]).set(drivername="postgresql+asyncpg")
if db_ssl_mode == "require":
    ssl_context = ssl.create_default_context()
    if not db_ssl_verify:
        # Some managed poolers present a private chain; transport encryption remains enabled.
        ssl_context.check_hostname = False
        ssl_context.verify_mode = ssl.CERT_NONE
    async_connect_args = {"ssl": ssl_context}
else:
    async_connect_args = {}

# Supabase Transaction Pooler uses PgBouncer transaction mode on port 6543.
# Disable prepared-statement caches because they cannot survive connection reuse.
if database_url.port == 6543:
    async_database_url = async_database_url.update_query_dict({"prepared_statement_cache_size": "0"})
    async_connect_args["statement_cache_size"] = 0
# Create a bounded asynchronous engine so cancelled requests do not occupy worker threads.
engine = create_async_engine(
    async_database_url,
    pool_pre_ping=True,
    pool_size=int(os.getenv("DB_POOL_SIZE", "10")),
    max_overflow=int(os.getenv("DB_MAX_OVERFLOW", "10")),
    pool_timeout=int(os.getenv("DB_POOL_TIMEOUT", "5")),
    connect_args=async_connect_args,
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
