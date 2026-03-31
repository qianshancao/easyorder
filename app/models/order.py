from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin


class Order(Base, TimestampMixin):
    __tablename__ = "orders"

    external_user_id: Mapped[str] = mapped_column(String(255), index=True)
    subscription_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("subscriptions.id"), nullable=True, default=None, index=True
    )
    type: Mapped[str] = mapped_column(String(20), index=True)
    amount: Mapped[int] = mapped_column(Integer)
    currency: Mapped[str] = mapped_column(String(3), default="CNY")
    status: Mapped[str] = mapped_column(String(20), default="pending", index=True)
    paid_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True, default=None)
    canceled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True, default=None)
