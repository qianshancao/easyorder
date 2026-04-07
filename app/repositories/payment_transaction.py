from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.payment_transaction import PaymentTransaction
from app.repositories.base import BaseRepository


class PaymentTransactionRepository(BaseRepository[PaymentTransaction]):
    def __init__(self, db: Session) -> None:
        super().__init__(PaymentTransaction, db)

    def get_by_payment_attempt_id(self, payment_attempt_id: int) -> list[PaymentTransaction]:
        stmt = (
            select(PaymentTransaction)
            .where(PaymentTransaction.payment_attempt_id == payment_attempt_id)
            .order_by(PaymentTransaction.id)
        )
        return list(self.db.execute(stmt).scalars().all())

    def get_by_order_id(self, order_id: int) -> list[PaymentTransaction]:
        stmt = select(PaymentTransaction).where(PaymentTransaction.order_id == order_id).order_by(PaymentTransaction.id)
        return list(self.db.execute(stmt).scalars().all())

    def get_by_channel_transaction_id(self, channel_transaction_id: str) -> PaymentTransaction | None:
        stmt = select(PaymentTransaction).where(PaymentTransaction.channel_transaction_id == channel_transaction_id)
        return self.db.execute(stmt).scalar_one_or_none()

    def list_filtered(
        self,
        *,
        payment_attempt_id: int | None = None,
        order_id: int | None = None,
        channel: str | None = None,
        status: str | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[PaymentTransaction]:
        stmt = select(PaymentTransaction).order_by(PaymentTransaction.id.desc())
        if payment_attempt_id is not None:
            stmt = stmt.where(PaymentTransaction.payment_attempt_id == payment_attempt_id)
        if order_id is not None:
            stmt = stmt.where(PaymentTransaction.order_id == order_id)
        if channel is not None:
            stmt = stmt.where(PaymentTransaction.channel == channel)
        if status is not None:
            stmt = stmt.where(PaymentTransaction.status == status)
        return list(self.db.execute(stmt.limit(limit).offset(offset)).scalars().all())
