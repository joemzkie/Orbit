from datetime import datetime

from sqlalchemy import DateTime, String, func
from sqlalchemy.orm import Mapped, mapped_column

from dbconn import Base


class User(Base):
    """Map user account records to the users database table."""

    # Set the physical table name used for user account records.
    __tablename__ = "users"

    # Store each user's email address as the table's unique primary key.
    email: Mapped[str] = mapped_column(String, primary_key=True)
    # Store an irreversible password hash used for authentication.
    password: Mapped[str] = mapped_column(String)
    # Record the timezone-aware timestamp when the user account was created.
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
