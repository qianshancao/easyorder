import logging
from datetime import UTC, datetime

from app.models.refund import Refund
from app.repositories.order import OrderRepository
from app.repositories.refund import RefundRepository
from app.schemas.refund import RefundCreate
from app.services.base import BaseService

logger = logging.getLogger(__name__)

VALID_REFUND_TRANSITIONS: dict[str, set[str]] = {
    "pending": {"success", "failed"},
    "success": set(),
    "failed": set(),
}


class RefundService(BaseService[Refund]):
    repo: RefundRepository  # type: ignore[assignment]

    def __init__(
        self,
        repo: RefundRepository,
        order_repo: OrderRepository,
    ) -> None:
        super().__init__(repo, domain_name="refund")
        self.order_repo = order_repo

    def create_refund(self, data: RefundCreate) -> Refund:
        # 验证金额大于 0
        if data.amount <= 0:
            raise ValueError(f"Refund amount must be positive, got {data.amount}")

        # 验证 Order 存在
        order = self.order_repo.get_by_id(data.order_id)
        if order is None:
            raise ValueError(f"Order {data.order_id} not found")

        # 验证订单已支付
        if order.status != "paid":
            raise ValueError(
                f"Order {data.order_id} is not paid (current status: {order.status})"
            )

        # 验证退款金额不超过订单金额
        if data.amount > order.amount:
            raise ValueError(
                f"Refund amount ({data.amount}) exceeds order amount ({order.amount})"
            )

        # 校验累计退款金额不超过订单金额
        existing_total = self.repo.get_total_refunded_amount(data.order_id)
        if existing_total + data.amount > order.amount:
            raise ValueError(
                f"Refund amount ({data.amount}) plus existing refunds ({existing_total}) "
                f"exceeds order amount ({order.amount})"
            )

        # 幂等检查: 同一订单相同金额不重复创建 pending 的退款
        existing = self.repo.get_pending_by_order_id_and_amount(
            data.order_id, data.amount
        )
        if existing is not None:
            logger.info(
                "refund.create_idempotent",
                extra={
                    "order_id": data.order_id,
                    "amount": data.amount,
                    "refund_id": existing.id,
                },
            )
            return existing

        refund = Refund(
            order_id=data.order_id,
            amount=data.amount,
            reason=data.reason,
            channel=data.channel,
            status="pending",
        )
        created = self.repo.create(refund)
        logger.info(
            "refund.created",
            extra={
                "refund_id": created.id,
                "order_id": created.order_id,
                "amount": created.amount,
                "channel": created.channel,
                "reason": created.reason,
            },
        )
        return created

    def get_refund(self, refund_id: int) -> Refund | None:
        return self.get(refund_id)

    def list_refunds(
        self,
        *,
        order_id: int | None = None,
        status: str | None = None,
        channel: str | None = None,
    ) -> list[Refund]:
        results = self.repo.list_filtered(
            order_id=order_id,
            status=status,
            channel=channel,
        )
        logger.info(
            "refund.listed",
            extra={
                "count": len(results),
                "filters": {
                    "order_id": order_id,
                    "status": status,
                    "channel": channel,
                },
            },
        )
        return results

    def mark_success(self, refund_id: int, channel_refund_id: str) -> Refund | None:
        refund = self.repo.get_by_id(refund_id)
        if refund is None:
            return None
        if refund.status == "success":
            logger.info(
                "refund.success_idempotent",
                extra={"refund_id": refund.id},
            )
            return refund
        self._validate_transition(refund.status, "success")
        refund.status = "success"
        refund.channel_refund_id = channel_refund_id
        refund.completed_at = datetime.now(UTC)
        updated = self.repo.update(refund)
        logger.info(
            "refund.success",
            extra={
                "refund_id": updated.id,
                "channel_refund_id": channel_refund_id,
            },
        )
        return updated

    def mark_failed(self, refund_id: int) -> Refund | None:
        refund = self.repo.get_by_id(refund_id)
        if refund is None:
            return None
        if refund.status == "failed":
            logger.info(
                "refund.failed_idempotent",
                extra={"refund_id": refund.id},
            )
            return refund
        self._validate_transition(refund.status, "failed")
        refund.status = "failed"
        updated = self.repo.update(refund)
        logger.info(
            "refund.failed",
            extra={"refund_id": updated.id},
        )
        return updated

    def _validate_transition(self, current: str, target: str) -> None:
        allowed = VALID_REFUND_TRANSITIONS.get(current, set())
        if target not in allowed:
            raise ValueError(f"Invalid status transition: {current} -> {target}")
