from sqlalchemy import ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin


class PaymentAttempt(Base, TimestampMixin):
    __tablename__ = "payment_attempts"

    order_id: Mapped[int] = mapped_column(Integer, ForeignKey("orders.id"), index=True)
    channel: Mapped[str] = mapped_column(String(20), index=True)
    amount: Mapped[int] = mapped_column(Integer)
    status: Mapped[str] = mapped_column(String(20), default="pending", index=True)
