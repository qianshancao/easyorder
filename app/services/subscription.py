import logging
from datetime import UTC, datetime, timedelta

from app.models.order import Order
from app.models.plan import Plan
from app.models.subscription import Subscription
from app.repositories.order import OrderRepository
from app.repositories.plan import PlanRepository
from app.repositories.subscription import SubscriptionRepository
from app.schemas.subscription import SubscriptionCreate
from app.services.base import BaseService
from app.services.proration import ProrationService

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

    def __init__(
        self,
        repo: SubscriptionRepository,
        plan_repo: PlanRepository,
        proration_service: ProrationService,
        order_repo: OrderRepository,
    ) -> None:
        super().__init__(repo, domain_name="subscription")
        self.plan_repo = plan_repo
        self.proration_service = proration_service
        self.order_repo = order_repo

    def create_subscription(self, data: SubscriptionCreate) -> Subscription:
        plan = self.plan_repo.get_by_id(data.plan_id)
        if plan is None:
            raise ValueError(f"Plan {data.plan_id} not found")
        if plan.status != "active":
            raise ValueError(f"Plan {data.plan_id} is not available")

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

    def upgrade_subscription(self, subscription_id: int, new_plan_id: int) -> tuple[Subscription, Order]:
        sub = self.repo.get_by_id(subscription_id)
        if sub is None:
            raise ValueError(f"Subscription {subscription_id} not found")
        if sub.status != "active":
            raise ValueError(f"Cannot upgrade subscription in {sub.status} status")

        new_plan = self.plan_repo.get_by_id(new_plan_id)
        if new_plan is None:
            raise ValueError(f"Plan {new_plan_id} not found")
        if new_plan.status != "active":
            raise ValueError(f"Plan {new_plan_id} is not available")
        if sub.plan_id == new_plan_id:
            raise ValueError("Cannot upgrade to the same plan")

        now = datetime.now(tz=UTC)
        # Ensure current_period_end is timezone-aware for SQLite compatibility
        period_end = sub.current_period_end
        if period_end.tzinfo is None:
            period_end = period_end.replace(tzinfo=UTC)
        remaining = (period_end - now).days
        if remaining < 0:
            remaining = 0

        old_base_price: int = sub.plan_snapshot.get("base_price", 0)  # type: ignore[arg-type]
        old_cycle: str = sub.plan_snapshot.get("cycle", "monthly")  # type: ignore[assignment]

        proration_amount = self.proration_service.calculate_proration(
            old_base_price=old_base_price,
            old_cycle=old_cycle,
            new_base_price=new_plan.base_price,
            new_cycle=new_plan.cycle,
            remaining_days=remaining,
        )

        # Save old plan_id for logging before updating
        old_plan_id = sub.plan_id

        # Update subscription
        sub.plan_id = new_plan.id
        sub.plan_snapshot = self._build_plan_snapshot(new_plan)
        new_cycle_days = CYCLE_DURATION_DAYS.get(new_plan.cycle, 30)
        sub.current_period_start = now
        sub.current_period_end = now + timedelta(days=new_cycle_days)
        updated_sub = self.repo.update(sub)

        # Create upgrade order
        order = Order(
            external_user_id=updated_sub.external_user_id,
            subscription_id=updated_sub.id,
            type="upgrade",
            amount=proration_amount,
            currency="CNY",
            status="pending",
        )
        created_order = self.order_repo.create(order)

        logger.info(
            "subscription.upgraded",
            extra={
                "subscription_id": updated_sub.id,
                "old_plan_id": old_plan_id,
                "new_plan_id": new_plan.id,
                "proration_amount": proration_amount,
                "order_id": created_order.id,
            },
        )
        return updated_sub, created_order

    def downgrade_subscription(self, subscription_id: int, new_plan_id: int) -> tuple[Subscription, Order]:
        sub = self.repo.get_by_id(subscription_id)
        if sub is None:
            raise ValueError(f"Subscription {subscription_id} not found")
        if sub.status != "active":
            raise ValueError(f"Cannot downgrade subscription in {sub.status} status")

        new_plan = self.plan_repo.get_by_id(new_plan_id)
        if new_plan is None:
            raise ValueError(f"Plan {new_plan_id} not found")
        if new_plan.status != "active":
            raise ValueError(f"Plan {new_plan_id} is not available")
        if sub.plan_id == new_plan_id:
            raise ValueError("Cannot downgrade to the same plan")

        now = datetime.now(tz=UTC)
        # Ensure current_period_end is timezone-aware for SQLite compatibility
        period_end = sub.current_period_end
        if period_end.tzinfo is None:
            period_end = period_end.replace(tzinfo=UTC)
        remaining = (period_end - now).days
        if remaining < 0:
            remaining = 0

        old_base_price: int = sub.plan_snapshot.get("base_price", 0)  # type: ignore[arg-type]
        old_cycle: str = sub.plan_snapshot.get("cycle", "monthly")  # type: ignore[assignment]

        proration_amount = self.proration_service.calculate_proration(
            old_base_price=old_base_price,
            old_cycle=old_cycle,
            new_base_price=new_plan.base_price,
            new_cycle=new_plan.cycle,
            remaining_days=remaining,
        )

        # For downgrade: negative proration means refund, but we don't actually refund
        # Order amount is capped at 0
        order_amount = max(0, proration_amount)

        # Save old plan_id for logging before updating
        old_plan_id = sub.plan_id

        # Update subscription
        sub.plan_id = new_plan.id
        sub.plan_snapshot = self._build_plan_snapshot(new_plan)
        new_cycle_days = CYCLE_DURATION_DAYS.get(new_plan.cycle, 30)
        sub.current_period_start = now
        sub.current_period_end = now + timedelta(days=new_cycle_days)
        updated_sub = self.repo.update(sub)

        # Create downgrade order
        order = Order(
            external_user_id=updated_sub.external_user_id,
            subscription_id=updated_sub.id,
            type="downgrade",
            amount=order_amount,
            currency="CNY",
            status="pending",
        )
        created_order = self.order_repo.create(order)

        logger.info(
            "subscription.downgraded",
            extra={
                "subscription_id": updated_sub.id,
                "old_plan_id": old_plan_id,
                "new_plan_id": new_plan.id,
                "proration_amount": proration_amount,
                "order_id": created_order.id,
            },
        )
        return updated_sub, created_order
