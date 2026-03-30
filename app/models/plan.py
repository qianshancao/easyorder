from sqlalchemy import JSON, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin


class Plan(Base, TimestampMixin):
    __tablename__ = "plans"

    name: Mapped[str] = mapped_column(String(100))
    cycle: Mapped[str] = mapped_column(String(20))
    base_price: Mapped[int] = mapped_column(Integer)  # unit: cents
    introductory_price: Mapped[int | None] = mapped_column(Integer, nullable=True, default=None)
    trial_price: Mapped[int | None] = mapped_column(Integer, nullable=True, default=None)
    trial_duration: Mapped[int | None] = mapped_column(Integer, nullable=True, default=None)
    features: Mapped[dict[str, object] | None] = mapped_column(JSON, nullable=True, default=None)
    renewal_rules: Mapped[dict[str, object] | None] = mapped_column(JSON, nullable=True, default=None)
    status: Mapped[str] = mapped_column(String(20), default="active")
