from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.payment_attempt import PaymentAttempt
from app.repositories.base import BaseRepository


class PaymentAttemptRepository(BaseRepository[PaymentAttempt]):
    def __init__(self, db: Session) -> None:
        super().__init__(PaymentAttempt, db)

    def get_by_order_id(self, order_id: int) -> list[PaymentAttempt]:
        stmt = (
            select(PaymentAttempt)
            .where(PaymentAttempt.order_id == order_id)
            .order_by(PaymentAttempt.id)
        )
        return list(self.db.execute(stmt).scalars().all())

    def get_pending_by_order_id(self, order_id: int) -> PaymentAttempt | None:
        stmt = select(PaymentAttempt).where(
            PaymentAttempt.order_id == order_id,
            PaymentAttempt.status == "pending",
        )
        return self.db.execute(stmt).scalar_one_or_none()

    def list_filtered(
        self,
        *,
        order_id: int | None = None,
        channel: str | None = None,
        status: str | None = None,
    ) -> list[PaymentAttempt]:
        stmt = select(PaymentAttempt).order_by(PaymentAttempt.id.desc())
        if order_id is not None:
            stmt = stmt.where(PaymentAttempt.order_id == order_id)
        if channel is not None:
            stmt = stmt.where(PaymentAttempt.channel == channel)
        if status is not None:
            stmt = stmt.where(PaymentAttempt.status == status)
        return list(self.db.execute(stmt).scalars().all())
