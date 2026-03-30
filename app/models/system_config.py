from sqlalchemy import JSON, String
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin


class SystemConfig(Base, TimestampMixin):
    __tablename__ = "system_configs"

    key: Mapped[str] = mapped_column(String(100), unique=True)
    value: Mapped[dict[str, object]] = mapped_column(JSON)
    description: Mapped[str | None] = mapped_column(String(255), nullable=True, default=None)
