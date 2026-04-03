"""Tests for RefundService."""

import pytest

from app.schemas.refund import RefundCreate
from app.services.refund import RefundService

from .conftest import _make_order_mock, _make_refund_mock


class TestCreateRefund:
    def test_create_success(self, mock_refund_repository, mock_order_repository) -> None:
        order = _make_order_mock(status="paid", amount=5000)
        mock_order_repository.get_by_id.return_value = order
        mock_refund_repository.get_total_refunded_amount.return_value = 0
        mock_refund_repository.get_pending_by_order_id_and_amount.return_value = None
        mock_refund_repository.create.side_effect = lambda e: e

        service = RefundService(mock_refund_repository, mock_order_repository)

        result = service.create_refund(RefundCreate(order_id=1, amount=3000, reason="用户申请退款", channel="alipay"))

        assert result.order_id == 1
        assert result.amount == 3000
        assert result.reason == "用户申请退款"
        assert result.channel == "alipay"
        assert result.status == "pending"

    def test_create_amount_must_be_positive(self, mock_refund_repository, mock_order_repository) -> None:
        service = RefundService(mock_refund_repository, mock_order_repository)

        with pytest.raises(ValueError, match="Refund amount must be positive"):
            service.create_refund(RefundCreate(order_id=1, amount=0, reason="test", channel="alipay"))

    def test_create_negative_amount_rejected_by_schema(self, mock_refund_repository, mock_order_repository) -> None:
        """负金额被 Pydantic schema 拒绝（ge=0 约束）。"""
        from pydantic import ValidationError

        with pytest.raises(ValidationError):
            RefundCreate(order_id=1, amount=-1000, reason="test", channel="alipay")

    def test_create_order_not_found(self, mock_refund_repository, mock_order_repository) -> None:
        mock_order_repository.get_by_id.return_value = None
        service = RefundService(mock_refund_repository, mock_order_repository)

        with pytest.raises(ValueError, match="Order 1 not found"):
            service.create_refund(RefundCreate(order_id=1, amount=3000, reason="test", channel="alipay"))

    def test_create_order_not_paid(self, mock_refund_repository, mock_order_repository) -> None:
        order = _make_order_mock(status="pending")
        mock_order_repository.get_by_id.return_value = order
        service = RefundService(mock_refund_repository, mock_order_repository)

        with pytest.raises(ValueError, match="Order 1 is not paid"):
            service.create_refund(RefundCreate(order_id=1, amount=3000, reason="test", channel="alipay"))

    def test_create_amount_exceeds_order_amount(self, mock_refund_repository, mock_order_repository) -> None:
        order = _make_order_mock(status="paid", amount=3000)
        mock_order_repository.get_by_id.return_value = order
        service = RefundService(mock_refund_repository, mock_order_repository)

        with pytest.raises(ValueError, match=r"Refund amount .* exceeds order amount"):
            service.create_refund(RefundCreate(order_id=1, amount=5000, reason="test", channel="alipay"))

    def test_create_cumulative_refund_exceeds_order_amount(self, mock_refund_repository, mock_order_repository) -> None:
        order = _make_order_mock(status="paid", amount=5000)
        mock_order_repository.get_by_id.return_value = order
        mock_refund_repository.get_total_refunded_amount.return_value = 3000
        service = RefundService(mock_refund_repository, mock_order_repository)

        with pytest.raises(ValueError, match=r"plus existing refunds"):
            service.create_refund(RefundCreate(order_id=1, amount=2500, reason="test", channel="alipay"))

    def test_create_cumulative_refund_equals_order_amount_allowed(
        self, mock_refund_repository, mock_order_repository
    ) -> None:
        order = _make_order_mock(status="paid", amount=5000)
        mock_order_repository.get_by_id.return_value = order
        mock_refund_repository.get_total_refunded_amount.return_value = 3000
        mock_refund_repository.get_pending_by_order_id_and_amount.return_value = None
        mock_refund_repository.create.side_effect = lambda e: e
        service = RefundService(mock_refund_repository, mock_order_repository)

        result = service.create_refund(RefundCreate(order_id=1, amount=2000, reason="test", channel="alipay"))

        assert result.amount == 2000

    def test_create_cumulative_refund_exactly_zero_allowed(self, mock_refund_repository, mock_order_repository) -> None:
        order = _make_order_mock(status="paid", amount=5000)
        mock_order_repository.get_by_id.return_value = order
        mock_refund_repository.get_total_refunded_amount.return_value = 0
        mock_refund_repository.get_pending_by_order_id_and_amount.return_value = None
        mock_refund_repository.create.side_effect = lambda e: e
        service = RefundService(mock_refund_repository, mock_order_repository)

        result = service.create_refund(RefundCreate(order_id=1, amount=3000, reason="test", channel="alipay"))

        assert result.amount == 3000

    def test_create_idempotent_same_order_and_amount(self, mock_refund_repository, mock_order_repository) -> None:
        order = _make_order_mock(status="paid", amount=5000)
        existing = _make_refund_mock()
        mock_order_repository.get_by_id.return_value = order
        mock_refund_repository.get_total_refunded_amount.return_value = 2000
        mock_refund_repository.get_pending_by_order_id_and_amount.return_value = existing

        service = RefundService(mock_refund_repository, mock_order_repository)

        result = service.create_refund(RefundCreate(order_id=1, amount=3000, reason="用户申请退款", channel="alipay"))

        assert result.id == existing.id
        mock_refund_repository.create.assert_not_called()

    def test_create_allows_different_amount(self, mock_refund_repository, mock_order_repository) -> None:
        order = _make_order_mock(status="paid", amount=5000)
        new_refund = _make_refund_mock(id=2, amount=2000)
        mock_order_repository.get_by_id.return_value = order
        mock_refund_repository.get_total_refunded_amount.return_value = 0
        mock_refund_repository.get_pending_by_order_id_and_amount.return_value = None
        mock_refund_repository.create.side_effect = lambda e: new_refund

        service = RefundService(mock_refund_repository, mock_order_repository)

        result = service.create_refund(RefundCreate(order_id=1, amount=2000, reason="部分退款", channel="alipay"))

        assert result.id == 2

    def test_create_with_all_channels(self, mock_refund_repository, mock_order_repository) -> None:
        order = _make_order_mock(status="paid", amount=5000)
        mock_order_repository.get_by_id.return_value = order
        mock_refund_repository.get_total_refunded_amount.return_value = 0
        mock_refund_repository.get_pending_by_order_id_and_amount.return_value = None
        mock_refund_repository.create.side_effect = lambda e: e

        service = RefundService(mock_refund_repository, mock_order_repository)

        for channel in ("alipay", "wechat", "stripe"):
            result = service.create_refund(RefundCreate(order_id=1, amount=1000, reason="test", channel=channel))
            assert result.channel == channel


class TestGetRefund:
    def test_found(self, mock_refund_repository, mock_order_repository) -> None:
        refund = _make_refund_mock()
        mock_refund_repository.get_by_id.return_value = refund
        service = RefundService(mock_refund_repository, mock_order_repository)

        assert service.get_refund(1) is refund

    def test_not_found(self, mock_refund_repository, mock_order_repository) -> None:
        mock_refund_repository.get_by_id.return_value = None
        service = RefundService(mock_refund_repository, mock_order_repository)

        assert service.get_refund(999) is None


class TestListRefunds:
    def test_returns_results(self, mock_refund_repository, mock_order_repository) -> None:
        refunds = [_make_refund_mock(), _make_refund_mock(id=2)]
        mock_refund_repository.list_filtered.return_value = refunds
        service = RefundService(mock_refund_repository, mock_order_repository)

        result = service.list_refunds()
        assert len(result) == 2

    def test_empty(self, mock_refund_repository, mock_order_repository) -> None:
        mock_refund_repository.list_filtered.return_value = []
        service = RefundService(mock_refund_repository, mock_order_repository)

        assert service.list_refunds() == []

    def test_with_filters(self, mock_refund_repository, mock_order_repository) -> None:
        refunds = [_make_refund_mock()]
        mock_refund_repository.list_filtered.return_value = refunds
        service = RefundService(mock_refund_repository, mock_order_repository)

        result = service.list_refunds(order_id=1, status="pending", channel="alipay")

        assert result == refunds
        mock_refund_repository.list_filtered.assert_called_once_with(order_id=1, status="pending", channel="alipay")


class TestMarkSuccess:
    def test_success_from_pending(self, mock_refund_repository, mock_order_repository) -> None:
        refund = _make_refund_mock(status="pending")
        mock_refund_repository.get_by_id.return_value = refund
        mock_refund_repository.update.side_effect = lambda e: e
        service = RefundService(mock_refund_repository, mock_order_repository)

        result = service.mark_success(1, "refund_12345")

        assert result.status == "success"
        assert result.channel_refund_id == "refund_12345"
        assert result.completed_at is not None

    def test_idempotent_already_success(self, mock_refund_repository, mock_order_repository) -> None:
        refund = _make_refund_mock(status="success", channel_refund_id="refund_123")
        mock_refund_repository.get_by_id.return_value = refund
        service = RefundService(mock_refund_repository, mock_order_repository)

        result = service.mark_success(1, "refund_456")

        assert result.status == "success"
        assert result.channel_refund_id == "refund_123"
        mock_refund_repository.update.assert_not_called()

    def test_invalid_from_failed(self, mock_refund_repository, mock_order_repository) -> None:
        refund = _make_refund_mock(status="failed")
        mock_refund_repository.get_by_id.return_value = refund
        service = RefundService(mock_refund_repository, mock_order_repository)

        with pytest.raises(ValueError, match="Invalid status transition"):
            service.mark_success(1, "refund_123")

    def test_not_found(self, mock_refund_repository, mock_order_repository) -> None:
        mock_refund_repository.get_by_id.return_value = None
        service = RefundService(mock_refund_repository, mock_order_repository)

        assert service.mark_success(999, "refund_123") is None


class TestMarkFailed:
    def test_failed_from_pending(self, mock_refund_repository, mock_order_repository) -> None:
        refund = _make_refund_mock(status="pending")
        mock_refund_repository.get_by_id.return_value = refund
        mock_refund_repository.update.side_effect = lambda e: e
        service = RefundService(mock_refund_repository, mock_order_repository)

        result = service.mark_failed(1)

        assert result.status == "failed"

    def test_idempotent_already_failed(self, mock_refund_repository, mock_order_repository) -> None:
        refund = _make_refund_mock(status="failed")
        mock_refund_repository.get_by_id.return_value = refund
        service = RefundService(mock_refund_repository, mock_order_repository)

        result = service.mark_failed(1)

        assert result.status == "failed"
        mock_refund_repository.update.assert_not_called()

    def test_invalid_from_success(self, mock_refund_repository, mock_order_repository) -> None:
        refund = _make_refund_mock(status="success")
        mock_refund_repository.get_by_id.return_value = refund
        service = RefundService(mock_refund_repository, mock_order_repository)

        with pytest.raises(ValueError, match="Invalid status transition"):
            service.mark_failed(1)

    def test_not_found(self, mock_refund_repository, mock_order_repository) -> None:
        mock_refund_repository.get_by_id.return_value = None
        service = RefundService(mock_refund_repository, mock_order_repository)

        assert service.mark_failed(999) is None


class TestRefundValidation:
    def test_order_status_canceled_raises_error(self, mock_refund_repository, mock_order_repository) -> None:
        order = _make_order_mock(status="canceled")
        mock_order_repository.get_by_id.return_value = order
        service = RefundService(mock_refund_repository, mock_order_repository)

        with pytest.raises(ValueError, match="Order 1 is not paid"):
            service.create_refund(RefundCreate(order_id=1, amount=1000, reason="test", channel="alipay"))

    def test_partial_refund_allowed(self, mock_refund_repository, mock_order_repository) -> None:
        order = _make_order_mock(status="paid", amount=5000)
        mock_order_repository.get_by_id.return_value = order
        mock_refund_repository.get_total_refunded_amount.return_value = 0
        mock_refund_repository.get_pending_by_order_id_and_amount.return_value = None
        mock_refund_repository.create.side_effect = lambda e: e

        service = RefundService(mock_refund_repository, mock_order_repository)

        result = service.create_refund(RefundCreate(order_id=1, amount=2000, reason="部分退款", channel="alipay"))

        assert result.amount == 2000

    def test_full_refund_allowed(self, mock_refund_repository, mock_order_repository) -> None:
        order = _make_order_mock(status="paid", amount=3000)
        mock_order_repository.get_by_id.return_value = order
        mock_refund_repository.get_total_refunded_amount.return_value = 0
        mock_refund_repository.get_pending_by_order_id_and_amount.return_value = None
        mock_refund_repository.create.side_effect = lambda e: e

        service = RefundService(mock_refund_repository, mock_order_repository)

        result = service.create_refund(RefundCreate(order_id=1, amount=3000, reason="全额退款", channel="alipay"))

        assert result.amount == 3000

    def test_refund_equals_order_amount_boundary(self, mock_refund_repository, mock_order_repository) -> None:
        order = _make_order_mock(status="paid", amount=3000)
        mock_order_repository.get_by_id.return_value = order
        mock_refund_repository.get_total_refunded_amount.return_value = 0
        mock_refund_repository.get_pending_by_order_id_and_amount.return_value = None
        mock_refund_repository.create.side_effect = lambda e: e

        service = RefundService(mock_refund_repository, mock_order_repository)

        # Should not raise - exact amount is allowed
        result = service.create_refund(RefundCreate(order_id=1, amount=3000, reason="test", channel="alipay"))

        assert result.amount == 3000

    def test_refund_exceeds_by_one(self, mock_refund_repository, mock_order_repository) -> None:
        order = _make_order_mock(status="paid", amount=3000)
        mock_order_repository.get_by_id.return_value = order
        service = RefundService(mock_refund_repository, mock_order_repository)

        with pytest.raises(ValueError, match="exceeds order amount"):
            service.create_refund(RefundCreate(order_id=1, amount=3001, reason="test", channel="alipay"))
