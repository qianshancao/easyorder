from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.subscription import Subscription
from app.repositories.base import BaseRepository


class SubscriptionRepository(BaseRepository[Subscription]):
    def __init__(self, db: Session) -> None:
        super().__init__(Subscription, db)

    def get_by_external_user_id(self, external_user_id: str) -> list[Subscription]:
        stmt = select(Subscription).where(Subscription.external_user_id == external_user_id).order_by(Subscription.id)
        return list(self.db.execute(stmt).scalars().all())
