from datetime import datetime

from sqlalchemy import DateTime, Integer, String, Text, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column

from dbconn import Base


class IdempotencyKey(Base):
    """Persist mutation results so retried requests cannot repeat side effects."""

    __tablename__ = "idempotency_keys"
    __table_args__ = (UniqueConstraint("scope", "key", name="uq_idempotency_scope_key"),)

    # Store the internal primary key for the idempotency record.
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    # Scope a client key to an HTTP method, route, and caller identity.
    scope: Mapped[str] = mapped_column(String(512), nullable=False)
    # Store the client-provided UUID-like request key.
    key: Mapped[str] = mapped_column(String(255), nullable=False)
    # Detect accidental reuse of a key for a different request body.
    request_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    # Track whether the first matching request is still executing or has completed.
    state: Mapped[str] = mapped_column(String(16), nullable=False, default="processing")
    # Store the successful HTTP status for an exact retry response.
    response_status: Mapped[int | None] = mapped_column(Integer, nullable=True)
    # Store the completed JSON or empty response body for exact replay.
    response_body: Mapped[str | None] = mapped_column(Text, nullable=True)
    # Store replay-safe headers such as Set-Cookie from a successful login.
    response_headers: Mapped[str | None] = mapped_column(Text, nullable=True)
    # Expire records after one day so the table remains bounded.
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    # Record when the first request registered its idempotency key.
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
