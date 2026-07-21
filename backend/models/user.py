from sqlalchemy import Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from dbconn import Base


class User(Base):
    """Reserved user model for the users router."""

    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    email: Mapped[str] = mapped_column(String, unique=True, index=True)
    password: Mapped[str] = mapped_column(String)
