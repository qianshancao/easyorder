import logging
from datetime import UTC, datetime

from app.models.order import Order
from app.repositories.order import OrderRepository
from app.repositories.subscription import SubscriptionRepository
from app.schemas.order import OrderCreate
from app.services.base import BaseService

logger = logging.getLogger(__name__)

VALID_ORDER_TRANSITIONS: dict[str, set[str]] = {
    "pending": {"paid", "canceled"},
    "paid": set(),
    "canceled": set(),
}

SUBSCRIPTION_ORDER_TYPES = {"opening", "renewal", "upgrade", "downgrade"}


class OrderService(BaseService[Order]):
    repo: OrderRepository  # type: ignore[assignment]

    def __init__(self, repo: OrderRepository, subscription_repo: SubscriptionRepository) -> None:
        super().__init__(repo, domain_name="order")
        self.subscription_repo = subscription_repo

    def create_order(self, data: OrderCreate) -> Order:
        self._validate_order_type_consistency(data.type, data.subscription_id)

        if data.type != "one_time" and data.subscription_id is not None:
            sub = self.subscription_repo.get_by_id(data.subscription_id)
            if sub is None:
                raise ValueError(f"Subscription {data.subscription_id} not found")

        order = Order(
            external_user_id=data.external_user_id,
            subscription_id=data.subscription_id,
            type=data.type,
            amount=data.amount,
            currency=data.currency,
            status="pending",
        )
        created = self.repo.create(order)
        logger.info(
            "order.created",
            extra={
                "order_id": created.id,
                "external_user_id": created.external_user_id,
                "type": created.type,
                "amount": created.amount,
            },
        )
        return created

    def get_order(self, order_id: int) -> Order | None:
        return self.get(order_id)

    def list_by_external_user_id(self, external_user_id: str) -> list[Order]:
        results = self.repo.get_by_external_user_id(external_user_id)
        logger.info(
            "order.listed_by_user",
            extra={"external_user_id": external_user_id, "count": len(results)},
        )
        return results

    def list_by_subscription_id(self, subscription_id: int) -> list[Order]:
        results = self.repo.get_by_subscription_id(subscription_id)
        logger.info(
            "order.listed_by_subscription",
            extra={"subscription_id": subscription_id, "count": len(results)},
        )
        return results

    def list_filtered(
        self,
        *,
        external_user_id: str | None = None,
        subscription_id: int | None = None,
        status: str | None = None,
        order_type: str | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[Order]:
        results = self.repo.list_filtered(
            external_user_id=external_user_id,
            subscription_id=subscription_id,
            status=status,
            order_type=order_type,
            limit=limit,
            offset=offset,
        )
        logger.info(
            "order.listed_filtered",
            extra={
                "count": len(results),
                "filters": {
                    "external_user_id": external_user_id,
                    "subscription_id": subscription_id,
                    "status": status,
                    "order_type": order_type,
                },
            },
        )
        return results

    def mark_as_paid(self, order_id: int) -> Order | None:
        order = self.repo.get_by_id(order_id)
        if order is None:
            return None
        if order.status == "paid":
            logger.info("order.pay_idempotent", extra={"order_id": order.id})
            return order
        self._validate_transition(order.status, "paid")
        order.status = "paid"
        order.paid_at = datetime.now(tz=UTC)
        updated = self.repo.update(order)
        logger.info("order.paid", extra={"order_id": updated.id})
        return updated

    def mark_as_canceled(self, order_id: int) -> Order | None:
        order = self.repo.get_by_id(order_id)
        if order is None:
            return None
        if order.status == "canceled":
            logger.info("order.cancel_idempotent", extra={"order_id": order.id})
            return order
        self._validate_transition(order.status, "canceled")
        order.status = "canceled"
        order.canceled_at = datetime.now(tz=UTC)
        updated = self.repo.update(order)
        logger.info("order.canceled", extra={"order_id": updated.id})
        return updated

    def _validate_transition(self, current: str, target: str) -> None:
        allowed = VALID_ORDER_TRANSITIONS.get(current, set())
        if target not in allowed:
            raise ValueError(f"Invalid status transition: {current} -> {target}")

    def _validate_order_type_consistency(self, order_type: str, subscription_id: int | None) -> None:
        if order_type == "one_time":
            if subscription_id is not None:
                raise ValueError("one_time order must have subscription_id set to None")
        else:
            if subscription_id is None:
                raise ValueError(f"{order_type} order requires subscription_id")
