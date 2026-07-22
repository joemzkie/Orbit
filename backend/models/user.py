from sqlalchemy import String
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
