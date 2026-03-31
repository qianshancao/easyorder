from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.order import Order
from app.repositories.base import BaseRepository


class OrderRepository(BaseRepository[Order]):
    def __init__(self, db: Session) -> None:
        super().__init__(Order, db)

    def get_by_external_user_id(self, external_user_id: str) -> list[Order]:
        stmt = select(Order).where(Order.external_user_id == external_user_id).order_by(Order.id)
        return list(self.db.execute(stmt).scalars().all())

    def get_by_subscription_id(self, subscription_id: int) -> list[Order]:
        stmt = select(Order).where(Order.subscription_id == subscription_id).order_by(Order.id)
        return list(self.db.execute(stmt).scalars().all())

    def list_filtered(
        self,
        *,
        external_user_id: str | None = None,
        subscription_id: int | None = None,
        status: str | None = None,
        order_type: str | None = None,
    ) -> list[Order]:
        stmt = select(Order).order_by(Order.id.desc())
        if external_user_id is not None:
            stmt = stmt.where(Order.external_user_id == external_user_id)
        if subscription_id is not None:
            stmt = stmt.where(Order.subscription_id == subscription_id)
        if status is not None:
            stmt = stmt.where(Order.status == status)
        if order_type is not None:
            stmt = stmt.where(Order.type == order_type)
        return list(self.db.execute(stmt).scalars().all())
