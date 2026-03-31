from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin


class Refund(Base, TimestampMixin):
    __tablename__ = "refunds"

    order_id: Mapped[int] = mapped_column(Integer, ForeignKey("orders.id"), nullable=False, index=True)
    amount: Mapped[int] = mapped_column(Integer, nullable=False)
    reason: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(String(20), default="pending", index=True)
    channel: Mapped[str] = mapped_column(String(20), nullable=False)
    channel_refund_id: Mapped[str | None] = mapped_column(String(128), nullable=True, default=None)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True, default=None)
