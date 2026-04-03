from datetime import UTC, datetime, timedelta

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.subscription import Subscription
from app.repositories.base import BaseRepository


class SubscriptionRepository(BaseRepository[Subscription]):
    def __init__(self, db: Session) -> None:
        super().__init__(Subscription, db)

    def get_by_external_user_id(self, external_user_id: str) -> list[Subscription]:
        stmt = select(Subscription).where(Subscription.external_user_id == external_user_id).order_by(Subscription.id)
        return list(self.db.execute(stmt).scalars().all())

    def get_expiring_subscriptions(self, *, days: int) -> list[Subscription]:
        """获取即将在指定天数内到期的 active 状态订阅。

        排除已取消(canceled_at 非 null)的订阅。
        按 current_period_end 升序排列。
        """
        cutoff = datetime.now(tz=UTC) + timedelta(days=days)
        stmt = (
            select(Subscription)
            .where(
                Subscription.status == "active",
                Subscription.canceled_at.is_(None),
                Subscription.current_period_end <= cutoff,
            )
            .order_by(Subscription.current_period_end)
        )
        return list(self.db.execute(stmt).scalars().all())

    def count_by_plan_id(self, plan_id: int) -> int:
        stmt = select(func.count()).select_from(Subscription).where(Subscription.plan_id == plan_id)
        return self.db.execute(stmt).scalar_one()

    def get_past_due_subscriptions(self) -> list[Subscription]:
        """获取所有 past_due 状态的订阅。

        Returns:
            past_due 状态的订阅列表
        """
        stmt = select(Subscription).where(Subscription.status == "past_due").order_by(Subscription.current_period_end)
        return list(self.db.execute(stmt).scalars().all())
