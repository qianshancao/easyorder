"""Tests for RenewalService."""

from datetime import UTC, datetime, timedelta
from unittest.mock import MagicMock

import pytest

from app.schemas.renewal import RenewalBatchResponse
from app.services.renewal import RenewalService

from .conftest import _make_order_mock, _make_subscription_mock


class TestProcessRenewals:
    """测试批量续费处理。"""

    def test_creates_renewal_orders_for_expiring_subscriptions(
        self,
        mock_subscription_repository,
        mock_order_repository,
        mock_payment_attempt_repository,
    ) -> None:
        """为即将到期的订阅创建续费订单和支付尝试。"""
        now = datetime.now(tz=UTC)
        sub = _make_subscription_mock(
            id=1,
            external_user_id="user_001",
            status="active",
            current_period_end=now + timedelta(days=2),
            plan_snapshot={"cycle": "monthly", "base_price": 3000},
        )
        mock_subscription_repository.get_expiring_subscriptions.return_value = [sub]

        order = _make_order_mock(id=10, type="renewal", amount=3000, subscription_id=1)
        mock_order_repository.create.return_value = order

        mock_payment_attempt_repository.create.side_effect = lambda p: p

        service = RenewalService(
            mock_subscription_repository,
            mock_order_repository,
            mock_payment_attempt_repository,
        )

        result = service.process_renewals(grace_period_days=7)

        assert isinstance(result, RenewalBatchResponse)
        assert result.processed_count == 1
        assert result.success_count == 1
        assert result.failure_count == 0
        assert len(result.attempts) == 1

        # Verify order was created
        mock_order_repository.create.assert_called_once()
        created_order = mock_order_repository.create.call_args[0][0]
        assert created_order.type == "renewal"
        assert created_order.amount == 3000
        assert created_order.subscription_id == 1

    def test_returns_empty_batch_when_no_expiring_subscriptions(
        self,
        mock_subscription_repository,
        mock_order_repository,
        mock_payment_attempt_repository,
    ) -> None:
        """没有即将到期的订阅时返回空结果。"""
        mock_subscription_repository.get_expiring_subscriptions.return_value = []

        service = RenewalService(
            mock_subscription_repository,
            mock_order_repository,
            mock_payment_attempt_repository,
        )

        result = service.process_renewals(grace_period_days=7)

        assert isinstance(result, RenewalBatchResponse)
        assert result.processed_count == 0
        assert result.success_count == 0
        assert result.failure_count == 0
        assert result.attempts == []

        mock_order_repository.create.assert_not_called()
        mock_payment_attempt_repository.create.assert_not_called()

    def test_handles_multiple_subscriptions(
        self,
        mock_subscription_repository,
        mock_order_repository,
        mock_payment_attempt_repository,
    ) -> None:
        """处理多个即将到期的订阅。"""
        now = datetime.now(tz=UTC)
        sub1 = _make_subscription_mock(
            id=1,
            external_user_id="user_001",
            status="active",
            current_period_end=now + timedelta(days=1),
            plan_snapshot={"cycle": "monthly", "base_price": 3000},
        )
        sub2 = _make_subscription_mock(
            id=2,
            external_user_id="user_002",
            status="active",
            current_period_end=now + timedelta(days=2),
            plan_snapshot={"cycle": "yearly", "base_price": 30000},
        )
        mock_subscription_repository.get_expiring_subscriptions.return_value = [sub1, sub2]

        order1 = _make_order_mock(id=10, type="renewal", amount=3000)
        order2 = _make_order_mock(id=11, type="renewal", amount=30000)
        mock_order_repository.create.side_effect = [order1, order2]
        mock_payment_attempt_repository.create.side_effect = lambda p: p

        service = RenewalService(
            mock_subscription_repository,
            mock_order_repository,
            mock_payment_attempt_repository,
        )

        result = service.process_renewals(grace_period_days=7)

        assert result.processed_count == 2
        assert result.success_count == 2
        assert result.failure_count == 0

        # Verify two orders were created with different amounts
        assert mock_order_repository.create.call_count == 2
        calls = mock_order_repository.create.call_args_list
        assert calls[0][0][0].amount == 3000
        assert calls[1][0][0].amount == 30000

    def test_handles_order_creation_failure_gracefully(
        self,
        mock_subscription_repository,
        mock_order_repository,
        mock_payment_attempt_repository,
    ) -> None:
        """订单创建失败时优雅降级。"""
        now = datetime.now(tz=UTC)
        sub1 = _make_subscription_mock(
            id=1,
            external_user_id="user_001",
            status="active",
            current_period_end=now + timedelta(days=2),
            plan_snapshot={"cycle": "monthly", "base_price": 3000},
        )
        sub2 = _make_subscription_mock(
            id=2,
            external_user_id="user_002",
            status="active",
            current_period_end=now + timedelta(days=3),
            plan_snapshot={"cycle": "monthly", "base_price": 3000},
        )
        mock_subscription_repository.get_expiring_subscriptions.return_value = [sub1, sub2]

        def create_order_with_failure(order):
            if order.subscription_id == 1:
                raise ValueError("Database error")
            order.id = 20
            order.created_at = datetime.now(tz=UTC)
            return order

        mock_order_repository.create.side_effect = create_order_with_failure
        mock_payment_attempt_repository.create.side_effect = lambda p: p

        service = RenewalService(
            mock_subscription_repository,
            mock_order_repository,
            mock_payment_attempt_repository,
        )

        result = service.process_renewals(grace_period_days=7)

        assert result.processed_count == 2
        assert result.success_count == 1
        assert result.failure_count == 1
        assert len(result.attempts) == 2

        # Verify failure details
        failure_attempt = next(a for a in result.attempts if a.subscription_id == 1)
        assert failure_attempt.success is False
        assert "Database error" in failure_attempt.error_message

    def test_uses_default_channel_alipay_for_payment_attempt(
        self,
        mock_subscription_repository,
        mock_order_repository,
        mock_payment_attempt_repository,
    ) -> None:
        """支付尝试默认使用 alipay 渠道。"""
        now = datetime.now(tz=UTC)
        sub = _make_subscription_mock(
            id=1,
            external_user_id="user_001",
            status="active",
            current_period_end=now + timedelta(days=2),
            plan_snapshot={"cycle": "monthly", "base_price": 3000},
        )
        mock_subscription_repository.get_expiring_subscriptions.return_value = [sub]

        order = _make_order_mock(id=10, type="renewal", amount=3000)
        mock_order_repository.create.return_value = order
        mock_payment_attempt_repository.create.side_effect = lambda p: p

        service = RenewalService(
            mock_subscription_repository,
            mock_order_repository,
            mock_payment_attempt_repository,
        )

        service.process_renewals(grace_period_days=7)

        # Verify payment attempt was created with alipay channel
        mock_payment_attempt_repository.create.assert_called_once()
        created_attempt = mock_payment_attempt_repository.create.call_args[0][0]
        assert created_attempt.channel == "alipay"
        assert created_attempt.amount == 3000


class TestHandleRenewalSuccess:
    """测试续费成功处理。"""

    def test_extends_subscription_period(
        self,
        mock_subscription_repository,
    ) -> None:
        """续费成功后延长订阅周期。"""
        now = datetime.now(tz=UTC)
        original_end = now + timedelta(days=5)
        sub = _make_subscription_mock(
            id=1,
            external_user_id="user_001",
            status="active",
            current_period_start=now - timedelta(days=25),
            current_period_end=original_end,
            plan_snapshot={"cycle": "monthly", "base_price": 3000},
        )
        mock_subscription_repository.get_by_id.return_value = sub
        mock_subscription_repository.update.side_effect = lambda e: e

        service = RenewalService(
            mock_subscription_repository,
            MagicMock(),
            MagicMock(),
        )

        service.handle_renewal_success(subscription_id=1)

        # Verify subscription period was extended by 30 days (monthly)
        expected_end = original_end + timedelta(days=30)
        assert sub.current_period_start == original_end
        assert sub.current_period_end == expected_end
        mock_subscription_repository.update.assert_called_once_with(sub)

    def test_supports_yearly_cycle(
        self,
        mock_subscription_repository,
    ) -> None:
        """支持年度周期。"""
        now = datetime.now(tz=UTC)
        original_end = now + timedelta(days=15)
        sub = _make_subscription_mock(
            id=1,
            external_user_id="user_001",
            status="active",
            current_period_start=now - timedelta(days=350),
            current_period_end=original_end,
            plan_snapshot={"cycle": "yearly", "base_price": 30000},
        )
        mock_subscription_repository.get_by_id.return_value = sub
        mock_subscription_repository.update.side_effect = lambda e: e

        service = RenewalService(
            mock_subscription_repository,
            MagicMock(),
            MagicMock(),
        )

        service.handle_renewal_success(subscription_id=1)

        # Verify subscription period was extended by 365 days (yearly)
        expected_end = original_end + timedelta(days=365)
        assert sub.current_period_end == expected_end

    def test_returns_none_when_subscription_not_found(
        self,
        mock_subscription_repository,
    ) -> None:
        """订阅不存在时返回 None。"""
        mock_subscription_repository.get_by_id.return_value = None

        service = RenewalService(
            mock_subscription_repository,
            MagicMock(),
            MagicMock(),
        )

        result = service.handle_renewal_success(subscription_id=999)

        assert result is None
        mock_subscription_repository.update.assert_not_called()


class TestHandleRenewalFailure:
    """测试续费失败处理。"""

    def test_sets_status_to_past_due(
        self,
        mock_subscription_repository,
    ) -> None:
        """续费失败后将订阅状态设为 past_due。"""
        now = datetime.now(tz=UTC)
        sub = _make_subscription_mock(
            id=1,
            external_user_id="user_001",
            status="active",
            current_period_end=now + timedelta(days=5),
            plan_snapshot={"cycle": "monthly", "base_price": 3000},
        )
        mock_subscription_repository.get_by_id.return_value = sub
        mock_subscription_repository.update.side_effect = lambda e: e

        service = RenewalService(
            mock_subscription_repository,
            MagicMock(),
            MagicMock(),
        )

        service.handle_renewal_failure(subscription_id=1, grace_period_days=7)

        assert sub.status == "past_due"
        mock_subscription_repository.update.assert_called_once_with(sub)

    def test_idempotent_when_already_past_due(
        self,
        mock_subscription_repository,
    ) -> None:
        """已经是 past_due 状态时幂等。"""
        now = datetime.now(tz=UTC)
        sub = _make_subscription_mock(
            id=1,
            external_user_id="user_001",
            status="past_due",
            current_period_end=now - timedelta(days=1),
            plan_snapshot={"cycle": "monthly", "base_price": 3000},
        )
        mock_subscription_repository.get_by_id.return_value = sub

        service = RenewalService(
            mock_subscription_repository,
            MagicMock(),
            MagicMock(),
        )

        service.handle_renewal_failure(subscription_id=1, grace_period_days=7)

        assert sub.status == "past_due"
        mock_subscription_repository.update.assert_not_called()

    def test_returns_none_when_subscription_not_found(
        self,
        mock_subscription_repository,
    ) -> None:
        """订阅不存在时返回 None。"""
        mock_subscription_repository.get_by_id.return_value = None

        service = RenewalService(
            mock_subscription_repository,
            MagicMock(),
            MagicMock(),
        )

        result = service.handle_renewal_failure(subscription_id=999, grace_period_days=7)

        assert result is None
        mock_subscription_repository.update.assert_not_called()


class TestProcessExpiredSubscriptions:
    """测试处理过期订阅。"""

    def test_moves_past_due_to_expired_after_grace_period(
        self,
        mock_subscription_repository,
    ) -> None:
        """宽限期过后将 past_due 订阅转为 expired。"""
        now = datetime.now(tz=UTC)
        sub = _make_subscription_mock(
            id=1,
            external_user_id="user_001",
            status="past_due",
            current_period_end=now - timedelta(days=10),  # 10天前到期
            plan_snapshot={"cycle": "monthly", "base_price": 3000},
        )
        mock_subscription_repository.get_past_due_subscriptions.return_value = [sub]
        mock_subscription_repository.update.side_effect = lambda e: e

        service = RenewalService(
            mock_subscription_repository,
            MagicMock(),
            MagicMock(),
        )

        result = service.process_expired_subscriptions(grace_period_days=7)

        assert result == 1
        assert sub.status == "expired"
        mock_subscription_repository.update.assert_called_once_with(sub)

    def test_skips_past_due_within_grace_period(
        self,
        mock_subscription_repository,
    ) -> None:
        """宽限期内的 past_due 订阅不处理。"""
        now = datetime.now(tz=UTC)
        sub = _make_subscription_mock(
            id=1,
            external_user_id="user_001",
            status="past_due",
            current_period_end=now - timedelta(days=3),  # 3天前到期（7天宽限期内）
            plan_snapshot={"cycle": "monthly", "base_price": 3000},
        )
        mock_subscription_repository.get_past_due_subscriptions.return_value = [sub]

        service = RenewalService(
            mock_subscription_repository,
            MagicMock(),
            MagicMock(),
        )

        result = service.process_expired_subscriptions(grace_period_days=7)

        assert result == 0
        assert sub.status == "past_due"
        mock_subscription_repository.update.assert_not_called()

    def test_returns_zero_when_no_past_due_subscriptions(
        self,
        mock_subscription_repository,
    ) -> None:
        """没有 past_due 订阅时返回 0。"""
        mock_subscription_repository.get_past_due_subscriptions.return_value = []

        service = RenewalService(
            mock_subscription_repository,
            MagicMock(),
            MagicMock(),
        )

        result = service.process_expired_subscriptions(grace_period_days=7)

        assert result == 0


class TestRenewSingleSubscription:
    """测试单笔订阅续费。"""

    def test_creates_renewal_order_for_subscription(
        self,
        mock_subscription_repository,
        mock_order_repository,
        mock_payment_attempt_repository,
    ) -> None:
        """为指定订阅创建续费订单。"""
        now = datetime.now(tz=UTC)
        sub = _make_subscription_mock(
            id=1,
            external_user_id="user_001",
            status="active",
            current_period_end=now + timedelta(days=5),
            plan_snapshot={"cycle": "monthly", "base_price": 3000},
        )
        mock_subscription_repository.get_by_id.return_value = sub

        order = _make_order_mock(id=10, type="renewal", amount=3000)
        mock_order_repository.create.return_value = order
        mock_payment_attempt_repository.create.side_effect = lambda p: p

        service = RenewalService(
            mock_subscription_repository,
            mock_order_repository,
            mock_payment_attempt_repository,
        )

        result = service.renew_subscription(subscription_id=1)

        assert result.success is True
        assert result.subscription_id == 1
        assert result.order_id == 10
        assert result.error_message is None

        mock_order_repository.create.assert_called_once()
        created_order = mock_order_repository.create.call_args[0][0]
        assert created_order.type == "renewal"
        assert created_order.amount == 3000

    def test_returns_error_when_subscription_not_found(
        self,
        mock_subscription_repository,
        mock_order_repository,
        mock_payment_attempt_repository,
    ) -> None:
        """订阅不存在时返回错误。"""
        mock_subscription_repository.get_by_id.return_value = None

        service = RenewalService(
            mock_subscription_repository,
            mock_order_repository,
            mock_payment_attempt_repository,
        )

        result = service.renew_subscription(subscription_id=999)

        assert result.success is False
        assert result.subscription_id == 999
        assert result.order_id is None
        assert "not found" in result.error_message.lower()

    def test_returns_error_when_subscription_canceled(
        self,
        mock_subscription_repository,
        mock_order_repository,
        mock_payment_attempt_repository,
    ) -> None:
        """已取消的订阅不能续费。"""
        now = datetime.now(tz=UTC)
        sub = _make_subscription_mock(
            id=1,
            external_user_id="user_001",
            status="active",
            current_period_end=now + timedelta(days=5),
            canceled_at=now - timedelta(days=1),  # 已取消
            plan_snapshot={"cycle": "monthly", "base_price": 3000},
        )
        mock_subscription_repository.get_by_id.return_value = sub

        service = RenewalService(
            mock_subscription_repository,
            mock_order_repository,
            mock_payment_attempt_repository,
        )

        result = service.renew_subscription(subscription_id=1)

        assert result.success is False
        assert "canceled" in result.error_message.lower()
        mock_order_repository.create.assert_not_called()


class TestRenewalStatusTransitionValidation:
    """测试续费场景的状态转换校验。"""

    def test_handle_failure_from_active_is_allowed(
        self,
        mock_subscription_repository,
    ) -> None:
        """active -> past_due 是合法的续费失败转换。"""
        now = datetime.now(tz=UTC)
        sub = _make_subscription_mock(
            id=1,
            external_user_id="user_001",
            status="active",
            current_period_end=now + timedelta(days=5),
            plan_snapshot={"cycle": "monthly", "base_price": 3000},
        )
        mock_subscription_repository.get_by_id.return_value = sub
        mock_subscription_repository.update.side_effect = lambda e: e

        service = RenewalService(
            mock_subscription_repository,
            MagicMock(),
            MagicMock(),
        )

        result = service.handle_renewal_failure(subscription_id=1, grace_period_days=7)

        assert result is not None
        assert result.status == "past_due"
        mock_subscription_repository.update.assert_called_once()

    def test_handle_failure_from_past_due_is_idempotent(
        self,
        mock_subscription_repository,
    ) -> None:
        """past_due 状态下再次失败应幂等返回。"""
        now = datetime.now(tz=UTC)
        sub = _make_subscription_mock(
            id=1,
            external_user_id="user_001",
            status="past_due",
            current_period_end=now - timedelta(days=1),
            plan_snapshot={"cycle": "monthly", "base_price": 3000},
        )
        mock_subscription_repository.get_by_id.return_value = sub

        service = RenewalService(
            mock_subscription_repository,
            MagicMock(),
            MagicMock(),
        )

        result = service.handle_renewal_failure(subscription_id=1, grace_period_days=7)

        assert result is sub
        mock_subscription_repository.update.assert_not_called()

    def test_handle_failure_from_trial_raises_error(
        self,
        mock_subscription_repository,
    ) -> None:
        """trial 状态不允许转换到 past_due（续费失败场景）。"""
        now = datetime.now(tz=UTC)
        sub = _make_subscription_mock(
            id=1,
            external_user_id="user_001",
            status="trial",
            current_period_end=now + timedelta(days=5),
            plan_snapshot={"cycle": "monthly", "base_price": 3000},
        )
        mock_subscription_repository.get_by_id.return_value = sub
        mock_subscription_repository.update.side_effect = lambda e: e

        service = RenewalService(
            mock_subscription_repository,
            MagicMock(),
            MagicMock(),
        )

        with pytest.raises(ValueError, match="Invalid renewal status transition"):
            service.handle_renewal_failure(subscription_id=1, grace_period_days=7)

    def test_handle_success_from_past_due_resets_to_active(
        self,
        mock_subscription_repository,
    ) -> None:
        """past_due -> active 是合法的续费成功转换（恢复服务）。"""
        now = datetime.now(tz=UTC)
        original_end = now + timedelta(days=5)
        sub = _make_subscription_mock(
            id=1,
            external_user_id="user_001",
            status="past_due",
            current_period_end=original_end,
            plan_snapshot={"cycle": "monthly", "base_price": 3000},
        )
        mock_subscription_repository.get_by_id.return_value = sub
        mock_subscription_repository.update.side_effect = lambda e: e

        service = RenewalService(
            mock_subscription_repository,
            MagicMock(),
            MagicMock(),
        )

        result = service.handle_renewal_success(subscription_id=1)

        assert result is not None
        assert result.status == "active"
        assert result.current_period_start == original_end
        mock_subscription_repository.update.assert_called_once()

    def test_handle_success_from_active_keeps_active(
        self,
        mock_subscription_repository,
    ) -> None:
        """active 状态下续费成功保持 active（正常续费）。"""
        now = datetime.now(tz=UTC)
        original_end = now + timedelta(days=5)
        sub = _make_subscription_mock(
            id=1,
            external_user_id="user_001",
            status="active",
            current_period_end=original_end,
            plan_snapshot={"cycle": "monthly", "base_price": 3000},
        )
        mock_subscription_repository.get_by_id.return_value = sub
        mock_subscription_repository.update.side_effect = lambda e: e

        service = RenewalService(
            mock_subscription_repository,
            MagicMock(),
            MagicMock(),
        )

        result = service.handle_renewal_success(subscription_id=1)

        assert result is not None
        assert result.status == "active"
        assert result.current_period_start == original_end

    def test_process_expired_from_past_due_to_expired(
        self,
        mock_subscription_repository,
    ) -> None:
        """past_due -> expired 是合法的宽限期结束转换。"""
        now = datetime.now(tz=UTC)
        sub = _make_subscription_mock(
            id=1,
            external_user_id="user_001",
            status="past_due",
            current_period_end=now - timedelta(days=10),
            plan_snapshot={"cycle": "monthly", "base_price": 3000},
        )
        mock_subscription_repository.get_past_due_subscriptions.return_value = [sub]
        mock_subscription_repository.update.side_effect = lambda e: e

        service = RenewalService(
            mock_subscription_repository,
            MagicMock(),
            MagicMock(),
        )

        result = service.process_expired_subscriptions(grace_period_days=7)

        assert result == 1
        assert sub.status == "expired"

    def test_handle_failure_from_canceled_raises_error(
        self,
        mock_subscription_repository,
    ) -> None:
        """canceled 状态的订阅调用 handle_renewal_failure 应抛出 ValueError。"""
        now = datetime.now(tz=UTC)
        sub = _make_subscription_mock(
            id=1,
            external_user_id="user_001",
            status="canceled",
            current_period_end=now + timedelta(days=5),
            plan_snapshot={"cycle": "monthly", "base_price": 3000},
        )
        mock_subscription_repository.get_by_id.return_value = sub

        service = RenewalService(
            mock_subscription_repository,
            MagicMock(),
            MagicMock(),
        )

        with pytest.raises(ValueError, match="Invalid renewal status transition"):
            service.handle_renewal_failure(subscription_id=1, grace_period_days=7)

    def test_handle_failure_from_expired_raises_error(
        self,
        mock_subscription_repository,
    ) -> None:
        """expired 状态的订阅调用 handle_renewal_failure 应抛出 ValueError。"""
        now = datetime.now(tz=UTC)
        sub = _make_subscription_mock(
            id=1,
            external_user_id="user_001",
            status="expired",
            current_period_end=now + timedelta(days=5),
            plan_snapshot={"cycle": "monthly", "base_price": 3000},
        )
        mock_subscription_repository.get_by_id.return_value = sub

        service = RenewalService(
            mock_subscription_repository,
            MagicMock(),
            MagicMock(),
        )

        with pytest.raises(ValueError, match="Invalid renewal status transition"):
            service.handle_renewal_failure(subscription_id=1, grace_period_days=7)

    def test_handle_success_with_quarterly_cycle_extends_90_days(
        self,
        mock_subscription_repository,
    ) -> None:
        """季度 cycle 的 handle_renewal_success 应延长 90 天。"""
        now = datetime.now(tz=UTC)
        original_end = now + timedelta(days=5)
        sub = _make_subscription_mock(
            id=1,
            external_user_id="user_001",
            status="past_due",
            current_period_end=original_end,
            plan_snapshot={"cycle": "quarterly", "base_price": 8000},
        )
        mock_subscription_repository.get_by_id.return_value = sub
        mock_subscription_repository.update.side_effect = lambda e: e

        service = RenewalService(
            mock_subscription_repository,
            MagicMock(),
            MagicMock(),
        )

        result = service.handle_renewal_success(subscription_id=1)

        assert result is not None
        assert result.status == "active"
        diff = result.current_period_end - original_end
        assert abs(diff.total_seconds() - timedelta(days=90).total_seconds()) < 5

    def test_handle_success_with_unknown_cycle_defaults_to_30_days(
        self,
        mock_subscription_repository,
    ) -> None:
        """未知 cycle 的 handle_renewal_success 应回退到 30 天。"""
        now = datetime.now(tz=UTC)
        original_end = now + timedelta(days=5)
        sub = _make_subscription_mock(
            id=1,
            external_user_id="user_001",
            status="past_due",
            current_period_end=original_end,
            plan_snapshot={"cycle": "custom", "base_price": 5000},
        )
        mock_subscription_repository.get_by_id.return_value = sub
        mock_subscription_repository.update.side_effect = lambda e: e

        service = RenewalService(
            mock_subscription_repository,
            MagicMock(),
            MagicMock(),
        )

        result = service.handle_renewal_success(subscription_id=1)

        assert result is not None
        assert result.status == "active"
        diff = result.current_period_end - original_end
        assert abs(diff.total_seconds() - timedelta(days=30).total_seconds()) < 5
