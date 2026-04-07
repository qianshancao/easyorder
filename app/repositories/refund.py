from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.refund import Refund
from app.repositories.base import BaseRepository


class RefundRepository(BaseRepository[Refund]):
    def __init__(self, db: Session) -> None:
        super().__init__(Refund, db)

    def get_by_order_id(self, order_id: int) -> list[Refund]:
        stmt = select(Refund).where(Refund.order_id == order_id).order_by(Refund.id)
        return list(self.db.execute(stmt).scalars().all())

    def get_pending_by_order_id_and_amount(self, order_id: int, amount: int) -> Refund | None:
        """Get pending refund by order ID and amount for idempotency check."""
        stmt = (
            select(Refund)
            .where(Refund.order_id == order_id)
            .where(Refund.amount == amount)
            .where(Refund.status == "pending")
            .order_by(Refund.id.desc())
        )
        return self.db.execute(stmt).scalars().first()

    def get_total_refunded_amount(self, order_id: int) -> int:
        """累计指定订单所有 pending + success 状态的退款总额。"""
        result = self.db.execute(
            select(func.coalesce(func.sum(Refund.amount), 0))
            .where(Refund.order_id == order_id)
            .where(Refund.status.in_(["pending", "success"]))
        ).scalar()
        # coalesce guarantees a non-None result
        return int(result)  # type: ignore[arg-type]

    def list_filtered(
        self,
        *,
        order_id: int | None = None,
        status: str | None = None,
        channel: str | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[Refund]:
        stmt = select(Refund).order_by(Refund.id.desc())
        if order_id is not None:
            stmt = stmt.where(Refund.order_id == order_id)
        if status is not None:
            stmt = stmt.where(Refund.status == status)
        if channel is not None:
            stmt = stmt.where(Refund.channel == channel)
        return list(self.db.execute(stmt.limit(limit).offset(offset)).scalars().all())
