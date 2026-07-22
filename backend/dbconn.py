import os
from collections.abc import Generator
from pathlib import Path

from dotenv import load_dotenv
from sqlalchemy import URL, create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

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

# Create the shared SQLAlchemy engine used to communicate with PostgreSQL.
engine = create_engine(database_url)
# Configure request-scoped sessions without implicit flushes or legacy autocommit.
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class Base(DeclarativeBase):
    """Provide the common SQLAlchemy declarative base for all ORM models."""

    pass


def get_db() -> Generator[Session, None, None]:
    """Provide one SQLAlchemy session for each request."""
    # Open a database session for the duration of the dependent request.
    db = SessionLocal()
    try:
        # Make the active session available to the endpoint handler.
        yield db
    finally:
        # Release the database connection even when request handling fails.
        db.close()
