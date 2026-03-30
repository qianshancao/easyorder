from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin


class OAuthClient(Base, TimestampMixin):
    __tablename__ = "oauth_clients"

    client_id: Mapped[str] = mapped_column(String(64), unique=True)
    client_secret: Mapped[str] = mapped_column(String(255))
    name: Mapped[str] = mapped_column(String(100))
    status: Mapped[str] = mapped_column(String(20), default="active")
