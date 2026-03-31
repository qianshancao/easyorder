import logging
from datetime import UTC, datetime

from app.models.payment_attempt import PaymentAttempt
from app.repositories.order import OrderRepository
from app.repositories.payment_attempt import PaymentAttemptRepository
from app.schemas.payment_attempt import PaymentAttemptCreate
from app.services.base import BaseService

logger = logging.getLogger(__name__)

VALID_PAYMENT_ATTEMPT_TRANSITIONS: dict[str, set[str]] = {
    "pending": {"success", "failed"},
    "success": set(),
    "failed": set(),
}


class PaymentAttemptService(BaseService[PaymentAttempt]):
    repo: PaymentAttemptRepository  # type: ignore[assignment]

    def __init__(
        self,
        repo: PaymentAttemptRepository,
        order_repo: OrderRepository,
    ) -> None:
        super().__init__(repo, domain_name="payment_attempt")
        self.order_repo = order_repo

    def create_attempt(self, data: PaymentAttemptCreate) -> PaymentAttempt:
        # 验证 Order 存在
        order = self.order_repo.get_by_id(data.order_id)
        if order is None:
            raise ValueError(f"Order {data.order_id} not found")

        # 幂等检查: 同一订单不重复创建 pending 的 attempt
        existing = self.repo.get_pending_by_order_id(data.order_id)
        if existing is not None:
            logger.info(
                "payment_attempt.create_idempotent",
                extra={"order_id": data.order_id, "attempt_id": existing.id},
            )
            return existing

        attempt = PaymentAttempt(
            order_id=data.order_id,
            channel=data.channel,
            amount=data.amount,
            status="pending",
        )
        created = self.repo.create(attempt)
        logger.info(
            "payment_attempt.created",
            extra={
                "attempt_id": created.id,
                "order_id": created.order_id,
                "channel": created.channel,
                "amount": created.amount,
            },
        )
        return created

    def get_attempt(self, attempt_id: int) -> PaymentAttempt | None:
        return self.get(attempt_id)

    def list_by_order(self, order_id: int) -> list[PaymentAttempt]:
        results = self.repo.get_by_order_id(order_id)
        logger.info(
            "payment_attempt.listed_by_order",
            extra={"order_id": order_id, "count": len(results)},
        )
        return results

    def list_filtered(
        self,
        *,
        order_id: int | None = None,
        channel: str | None = None,
        status: str | None = None,
    ) -> list[PaymentAttempt]:
        results = self.repo.list_filtered(
            order_id=order_id,
            channel=channel,
            status=status,
        )
        logger.info(
            "payment_attempt.listed_filtered",
            extra={
                "count": len(results),
                "filters": {
                    "order_id": order_id,
                    "channel": channel,
                    "status": status,
                },
            },
        )
        return results

    def mark_as_success(
        self, attempt_id: int, channel_transaction_id: str
    ) -> PaymentAttempt | None:
        attempt = self.repo.get_by_id(attempt_id)
        if attempt is None:
            return None
        if attempt.status == "success":
            logger.info(
                "payment_attempt.success_idempotent",
                extra={"attempt_id": attempt.id},
            )
            return attempt
        self._validate_transition(attempt.status, "success")
        attempt.status = "success"
        attempt.channel_transaction_id = channel_transaction_id
        updated = self.repo.update(attempt)
        logger.info(
            "payment_attempt.success",
            extra={
                "attempt_id": updated.id,
                "channel_transaction_id": channel_transaction_id,
            },
        )

        # 支付成功后自动联动订单状态
        order = self.order_repo.get_by_id(updated.order_id)
        if order is not None and order.status == "pending":
            order.status = "paid"
            order.paid_at = datetime.now(tz=UTC)
            self.order_repo.update(order)
            logger.info(
                "payment_attempt.order_paid",
                extra={
                    "order_id": order.id,
                    "payment_attempt_id": updated.id,
                },
            )

        return updated

    def mark_as_failed(self, attempt_id: int) -> PaymentAttempt | None:
        attempt = self.repo.get_by_id(attempt_id)
        if attempt is None:
            return None
        if attempt.status == "failed":
            logger.info(
                "payment_attempt.failed_idempotent",
                extra={"attempt_id": attempt.id},
            )
            return attempt
        self._validate_transition(attempt.status, "failed")
        attempt.status = "failed"
        updated = self.repo.update(attempt)
        logger.info(
            "payment_attempt.failed",
            extra={"attempt_id": updated.id},
        )
        return updated

    def _validate_transition(self, current: str, target: str) -> None:
        allowed = VALID_PAYMENT_ATTEMPT_TRANSITIONS.get(current, set())
        if target not in allowed:
            raise ValueError(f"Invalid status transition: {current} -> {target}")
