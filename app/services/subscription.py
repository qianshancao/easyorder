import logging
from datetime import UTC, datetime, timedelta

from app.models.plan import Plan
from app.models.subscription import Subscription
from app.repositories.plan import PlanRepository
from app.repositories.subscription import SubscriptionRepository
from app.schemas.subscription import SubscriptionCreate
from app.services.base import BaseService

logger = logging.getLogger(__name__)

VALID_TRANSITIONS: dict[str, set[str]] = {
    "trial": {"active"},
    "active": {"past_due", "canceled"},
    "past_due": {"active", "expired", "canceled"},
    "canceled": set(),
    "expired": set(),
}

CYCLE_DURATION_DAYS: dict[str, int] = {
    "monthly": 30,
    "quarterly": 90,
    "yearly": 365,
}


class SubscriptionService(BaseService[Subscription]):
    repo: SubscriptionRepository  # type: ignore[assignment]

    def __init__(self, repo: SubscriptionRepository, plan_repo: PlanRepository) -> None:
        super().__init__(repo, domain_name="subscription")
        self.plan_repo = plan_repo

    def create_subscription(self, data: SubscriptionCreate) -> Subscription:
        plan = self.plan_repo.get_by_id(data.plan_id)
        if plan is None:
            raise ValueError(f"Plan {data.plan_id} not found")

        snapshot = self._build_plan_snapshot(plan)
        now = datetime.now(tz=UTC)

        if plan.trial_duration is not None and plan.trial_duration > 0:
            status = "trial"
            period_end = now + timedelta(days=plan.trial_duration)
        else:
            status = "active"
            period_end = now + timedelta(days=CYCLE_DURATION_DAYS.get(plan.cycle, 30))

        subscription = Subscription(
            external_user_id=data.external_user_id,
            plan_id=plan.id,
            plan_snapshot=snapshot,
            status=status,
            current_period_start=now,
            current_period_end=period_end,
        )
        created = self.repo.create(subscription)
        logger.info(
            "subscription.created",
            extra={
                "subscription_id": created.id,
                "external_user_id": created.external_user_id,
                "plan_id": plan.id,
                "status": created.status,
            },
        )
        return created

    def get_subscription(self, subscription_id: int) -> Subscription | None:
        return self.get(subscription_id)

    def list_by_external_user_id(self, external_user_id: str) -> list[Subscription]:
        results = self.repo.get_by_external_user_id(external_user_id)
        logger.info(
            "subscription.listed_by_user",
            extra={"external_user_id": external_user_id, "count": len(results)},
        )
        return results

    def cancel_subscription(self, subscription_id: int) -> Subscription | None:
        subscription = self.repo.get_by_id(subscription_id)
        if subscription is None:
            return None
        self._validate_transition(subscription.status, "canceled")
        subscription.status = "canceled"
        subscription.canceled_at = datetime.now(tz=UTC)
        updated = self.repo.update(subscription)
        logger.info(
            "subscription.canceled",
            extra={
                "subscription_id": updated.id,
                "external_user_id": updated.external_user_id,
            },
        )
        return updated

    def reactivate_subscription(self, subscription_id: int) -> Subscription | None:
        subscription = self.repo.get_by_id(subscription_id)
        if subscription is None:
            return None
        self._validate_transition(subscription.status, "active")
        subscription.status = "active"
        subscription.canceled_at = None
        cycle_days = CYCLE_DURATION_DAYS.get(str(subscription.plan_snapshot.get("cycle", "monthly")), 30)
        now = datetime.now(tz=UTC)
        subscription.current_period_start = now
        subscription.current_period_end = now + timedelta(days=cycle_days)
        updated = self.repo.update(subscription)
        logger.info(
            "subscription.reactivated",
            extra={"subscription_id": updated.id},
        )
        return updated

    def _build_plan_snapshot(self, plan: Plan) -> dict[str, object]:
        return {
            "name": plan.name,
            "cycle": plan.cycle,
            "base_price": plan.base_price,
            "introductory_price": plan.introductory_price,
            "trial_price": plan.trial_price,
            "trial_duration": plan.trial_duration,
            "features": plan.features,
        }

    def _validate_transition(self, current: str, target: str) -> None:
        allowed = VALID_TRANSITIONS.get(current, set())
        if target not in allowed:
            raise ValueError(f"Invalid status transition: {current} -> {target}")
