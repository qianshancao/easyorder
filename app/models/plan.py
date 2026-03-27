from datetime import UTC, datetime

from sqlalchemy import JSON, DateTime, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


def _utcnow() -> datetime:
    return datetime.now(tz=UTC)


class Plan(Base):
    __tablename__ = "plans"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(100))
    cycle: Mapped[str] = mapped_column(String(20))
    base_price: Mapped[int] = mapped_column(Integer)  # unit: cents
    introductory_price: Mapped[int | None] = mapped_column(Integer, nullable=True, default=None)
    trial_price: Mapped[int | None] = mapped_column(Integer, nullable=True, default=None)
    trial_duration: Mapped[int | None] = mapped_column(Integer, nullable=True, default=None)
    features: Mapped[dict[str, object] | None] = mapped_column(JSON, nullable=True, default=None)
    renewal_rules: Mapped[dict[str, object] | None] = mapped_column(JSON, nullable=True, default=None)
    status: Mapped[str] = mapped_column(String(20), default="active")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)
    updated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True, default=None)
