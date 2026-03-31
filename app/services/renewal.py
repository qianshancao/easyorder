"""自动续费服务。

负责处理订阅的自动续费逻辑:
- 检测即将到期的订阅并创建续费订单
- 处理续费成功后延长订阅周期
- 处理续费失败后设置宽限期状态
- 处理宽限期后的过期订阅
"""

import logging
from datetime import UTC, datetime, timedelta

from app.models.order import Order
from app.models.payment_attempt import PaymentAttempt
from app.models.subscription import Subscription
from app.repositories.order import OrderRepository
from app.repositories.payment_attempt import PaymentAttemptRepository
from app.repositories.subscription import SubscriptionRepository
from app.schemas.renewal import RenewalAttemptResponse, RenewalBatchResponse

logger = logging.getLogger(__name__)

# 续费场景的状态转换规则
RENEWAL_TRANSITIONS: dict[str, set[str]] = {
    "active": {"past_due"},  # 续费失败: active -> past_due
    "past_due": {"active", "expired"},  # 续费成功: past_due -> active; 宽限期结束: past_due -> expired
}

# 复用 SubscriptionService 的周期天数常量
CYCLE_DURATION_DAYS: dict[str, int] = {
    "monthly": 30,
    "quarterly": 90,
    "yearly": 365,
}


class RenewalService:
    """自动续费服务。

   编排服务，协调 SubscriptionRepository、OrderRepository 和
    PaymentAttemptRepository 完成续费流程。
    """

    def __init__(
        self,
        subscription_repo: SubscriptionRepository,
        order_repo: OrderRepository,
        payment_attempt_repo: PaymentAttemptRepository,
    ) -> None:
        self._subscription_repo = subscription_repo
        self._order_repo = order_repo
        self._payment_attempt_repo = payment_attempt_repo

    def process_renewals(self, *, grace_period_days: int) -> RenewalBatchResponse:
        """批量处理即将到期的订阅，创建续费订单和支付尝试。

        Args:
            grace_period_days: 提前多少天开始处理续费

        Returns:
            RenewalBatchResponse: 批量处理结果
        """
        expiring_subs = self._subscription_repo.get_expiring_subscriptions(days=grace_period_days)
        attempts: list[RenewalAttemptResponse] = []
        success_count = 0
        failure_count = 0

        for sub in expiring_subs:
            attempt = self._create_renewal_for_subscription(sub)
            attempts.append(attempt)
            if attempt.success:
                success_count += 1
            else:
                failure_count += 1

        logger.info(
            "renewal.batch_processed",
            extra={
                "processed_count": len(attempts),
                "success_count": success_count,
                "failure_count": failure_count,
                "grace_period_days": grace_period_days,
            },
        )

        return RenewalBatchResponse(
            processed_count=len(attempts),
            success_count=success_count,
            failure_count=failure_count,
            attempts=attempts,
        )

    def handle_renewal_success(self, subscription_id: int) -> Subscription | None:
        """处理续费成功，延长订阅周期。

        续费成功后，订阅状态应重置为 active。

        Args:
            subscription_id: 订阅ID

        Returns:
            更新后的订阅，不存在时返回 None
        """
        sub = self._subscription_repo.get_by_id(subscription_id)
        if sub is None:
            logger.warning("renewal.success.subscription_not_found", extra={"subscription_id": subscription_id})
            return None

        # 如果订阅在 past_due 状态，续费成功后应恢复为 active
        previous_status = sub.status
        if sub.status == "past_due":
            sub.status = "active"

        # 计算新的周期
        cycle: str = sub.plan_snapshot.get("cycle", "monthly")  # type: ignore[assignment]
        days_to_add = self._get_cycle_days(cycle)

        # 新周期从旧 current_period_end 开始
        old_end = sub.current_period_end
        sub.current_period_start = old_end
        sub.current_period_end = old_end + timedelta(days=days_to_add)

        updated = self._subscription_repo.update(sub)
        logger.info(
            "renewal.success",
            extra={
                "subscription_id": updated.id,
                "previous_status": previous_status,
                "new_status": updated.status,
                "cycle": cycle,
                "days_added": days_to_add,
            },
        )
        return updated

    def handle_renewal_failure(self, subscription_id: int, grace_period_days: int) -> Subscription | None:
        """处理续费失败，将订阅设为 past_due 状态。

        仅允许 active -> past_due 的状态转换。

        Args:
            subscription_id: 订阅ID
            grace_period_days: 宽限期天数（用于日志记录）

        Returns:
            更新后的订阅，不存在或状态转换非法时返回 None
        """
        sub = self._subscription_repo.get_by_id(subscription_id)
        if sub is None:
            logger.warning("renewal.failure.subscription_not_found", extra={"subscription_id": subscription_id})
            return None

        # 幂等：已经是 past_due 则不重复处理
        if sub.status == "past_due":
            logger.debug("renewal.failure.already_past_due", extra={"subscription_id": subscription_id})
            return sub

        # 状态转换校验：仅允许 active -> past_due
        self._validate_renewal_transition(sub.status, "past_due")

        previous_status = sub.status
        sub.status = "past_due"
        updated = self._subscription_repo.update(sub)
        logger.info(
            "renewal.failure",
            extra={
                "subscription_id": updated.id,
                "previous_status": previous_status,
                "grace_period_days": grace_period_days,
            },
        )
        return updated

    def process_expired_subscriptions(self, grace_period_days: int) -> int:
        """处理过期的订阅，将 past_due 且超过宽限期的订阅设为 expired。

        Args:
            grace_period_days: 宽限期天数

        Returns:
            设置为 expired 的订阅数量
        """
        # 获取所有 past_due 订阅（在 repository 层过滤）
        past_due_subs = self._subscription_repo.get_past_due_subscriptions()

        if not past_due_subs:
            return 0

        expired_count = 0
        cutoff = datetime.now(tz=UTC) - timedelta(days=grace_period_days)

        for sub in past_due_subs:
            # 确保 current_period_end 是时区感知的再比较
            sub_end = sub.current_period_end
            if sub_end:
                # 如果 sub_end 是 naive（无时区），假设为 UTC
                if sub_end.tzinfo is None:
                    sub_end = sub_end.replace(tzinfo=UTC)
                if sub_end < cutoff:
                    # 状态转换校验：past_due -> expired
                    self._validate_renewal_transition(sub.status, "expired")
                    sub.status = "expired"
                    self._subscription_repo.update(sub)
                    expired_count += 1

        logger.info(
            "renewal.expired_processed",
            extra={
                "expired_count": expired_count,
                "grace_period_days": grace_period_days,
            },
        )

        return expired_count

    def renew_subscription(self, subscription_id: int) -> RenewalAttemptResponse:
        """为单个订阅创建续费订单。

        Args:
            subscription_id: 订阅ID

        Returns:
            RenewalAttemptResponse: 续费尝试结果
        """
        sub = self._subscription_repo.get_by_id(subscription_id)
        if sub is None:
            return RenewalAttemptResponse(
                subscription_id=subscription_id,
                order_id=None,
                success=False,
                error_message=f"Subscription {subscription_id} not found",
                created_at=datetime.now(tz=UTC),
            )

        # 检查订阅是否已取消
        if sub.canceled_at is not None:
            return RenewalAttemptResponse(
                subscription_id=subscription_id,
                order_id=None,
                success=False,
                error_message="Subscription is canceled",
                created_at=datetime.now(tz=UTC),
            )

        return self._create_renewal_for_subscription(sub)

    def _create_renewal_for_subscription(self, sub: Subscription) -> RenewalAttemptResponse:
        """为订阅创建续费订单和支付尝试。

        Args:
            sub: 订阅对象

        Returns:
            RenewalAttemptResponse: 续费尝试结果
        """
        now = datetime.now(tz=UTC)
        try:
            # 从 plan_snapshot 获取价格
            amount: int = int(sub.plan_snapshot.get("base_price", 0))  # type: ignore[arg-type]

            # 创建续费订单
            order = Order(
                external_user_id=sub.external_user_id,
                subscription_id=sub.id,
                type="renewal",
                amount=amount,
                currency="CNY",
                status="pending",
            )
            created_order = self._order_repo.create(order)

            # 处理 create 返回 None 的情况（mock 场景）
            if created_order is None or not created_order.id:  # type: ignore[truthy-operand]
                raise ValueError("Failed to create order")

            # 创建支付尝试（默认使用 alipay）
            attempt = PaymentAttempt(
                order_id=created_order.id,
                channel="alipay",
                amount=amount,
                status="pending",
            )
            self._payment_attempt_repo.create(attempt)

            return RenewalAttemptResponse(
                subscription_id=sub.id,
                order_id=created_order.id,
                success=True,
                error_message=None,
                created_at=now,
            )

        except Exception as e:
            return RenewalAttemptResponse(
                subscription_id=sub.id,
                order_id=None,
                success=False,
                error_message=str(e),
                created_at=now,
            )

    def _get_cycle_days(self, cycle: str) -> int:
        """获取周期对应的天数。

        Args:
            cycle: 周期类型（monthly/quarterly/yearly）

        Returns:
            天数
        """
        return CYCLE_DURATION_DAYS.get(cycle, 30)

    def _validate_renewal_transition(self, current: str, target: str) -> None:
        """验证续费场景的状态转换是否合法。

        Args:
            current: 当前状态
            target: 目标状态

        Raises:
            ValueError: 状态转换非法
        """
        allowed = RENEWAL_TRANSITIONS.get(current, set())
        if target not in allowed:
            raise ValueError(f"Invalid renewal status transition: {current} -> {target}")
