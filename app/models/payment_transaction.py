from sqlalchemy import ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin


class PaymentTransaction(Base, TimestampMixin):
    """PaymentTransaction - channel-confirmed transaction record.

    Separated from PaymentAttempt: Attempt is "I requested payment",
    Transaction is "channel confirmed the transaction".
    Created automatically in mark_as_success for reconciliation and refund association.
    """

    __tablename__ = "payment_transactions"

    payment_attempt_id: Mapped[int] = mapped_column(Integer, ForeignKey("payment_attempts.id"), index=True)
    order_id: Mapped[int] = mapped_column(Integer, ForeignKey("orders.id"), index=True)
    channel: Mapped[str] = mapped_column(String(20), index=True)
    amount: Mapped[int] = mapped_column(Integer)
    currency: Mapped[str] = mapped_column(String(3), default="CNY")
    channel_transaction_id: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    raw_callback_data: Mapped[str | None] = mapped_column(Text, nullable=True, default=None)
    status: Mapped[str] = mapped_column(String(20), default="confirmed", index=True)
