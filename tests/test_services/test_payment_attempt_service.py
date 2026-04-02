"""Tests for PaymentAttemptService."""

import pytest

from app.schemas.payment_attempt import PaymentAttemptCreate
from app.services.payment_attempt import PaymentAttemptService

from .conftest import _make_attempt_mock, _make_order_mock


class TestCreateAttempt:
    def test_create_success(self, mock_payment_attempt_repository, mock_order_repository) -> None:
        order = _make_order_mock()
        mock_order_repository.get_by_id.return_value = order
        mock_payment_attempt_repository.get_pending_by_order_id.return_value = None
        mock_payment_attempt_repository.create.side_effect = lambda e: e

        service = PaymentAttemptService(mock_payment_attempt_repository, mock_order_repository)

        result = service.create_attempt(PaymentAttemptCreate(order_id=1, channel="alipay", amount=3000))

        assert result.order_id == 1
        assert result.channel == "alipay"
        assert result.amount == 3000
        assert result.status == "pending"

    def test_create_order_not_found(self, mock_payment_attempt_repository, mock_order_repository) -> None:
        mock_order_repository.get_by_id.return_value = None
        service = PaymentAttemptService(mock_payment_attempt_repository, mock_order_repository)

        with pytest.raises(ValueError, match="Order 1 not found"):
            service.create_attempt(PaymentAttemptCreate(order_id=1, channel="alipay", amount=3000))

    def test_create_idempotent_returns_existing_pending(
        self, mock_payment_attempt_repository, mock_order_repository
    ) -> None:
        order = _make_order_mock()
        existing = _make_attempt_mock()
        mock_order_repository.get_by_id.return_value = order
        mock_payment_attempt_repository.get_pending_by_order_id.return_value = existing

        service = PaymentAttemptService(mock_payment_attempt_repository, mock_order_repository)

        result = service.create_attempt(PaymentAttemptCreate(order_id=1, channel="alipay", amount=3000))

        assert result.id == existing.id
        mock_payment_attempt_repository.create.assert_not_called()

    def test_create_allows_new_after_failed(self, mock_payment_attempt_repository, mock_order_repository) -> None:
        order = _make_order_mock()
        new_attempt = _make_attempt_mock(id=2)
        mock_order_repository.get_by_id.return_value = order
        mock_payment_attempt_repository.get_pending_by_order_id.return_value = None
        mock_payment_attempt_repository.create.side_effect = lambda e: new_attempt

        service = PaymentAttemptService(mock_payment_attempt_repository, mock_order_repository)

        result = service.create_attempt(PaymentAttemptCreate(order_id=1, channel="alipay", amount=3000))

        assert result.id == 2


class TestGetAttempt:
    def test_found(self, mock_payment_attempt_repository, mock_order_repository) -> None:
        attempt = _make_attempt_mock()
        mock_payment_attempt_repository.get_by_id.return_value = attempt
        service = PaymentAttemptService(mock_payment_attempt_repository, mock_order_repository)

        assert service.get_attempt(1) is attempt

    def test_not_found(self, mock_payment_attempt_repository, mock_order_repository) -> None:
        mock_payment_attempt_repository.get_by_id.return_value = None
        service = PaymentAttemptService(mock_payment_attempt_repository, mock_order_repository)

        assert service.get_attempt(999) is None


class TestListByOrder:
    def test_returns_results(self, mock_payment_attempt_repository, mock_order_repository) -> None:
        attempts = [_make_attempt_mock(), _make_attempt_mock(id=2)]
        mock_payment_attempt_repository.get_by_order_id.return_value = attempts
        service = PaymentAttemptService(mock_payment_attempt_repository, mock_order_repository)

        result = service.list_by_order(1)
        assert len(result) == 2

    def test_empty(self, mock_payment_attempt_repository, mock_order_repository) -> None:
        mock_payment_attempt_repository.get_by_order_id.return_value = []
        service = PaymentAttemptService(mock_payment_attempt_repository, mock_order_repository)

        assert service.list_by_order(999) == []


class TestMarkAsSuccess:
    def test_success_from_pending(self, mock_payment_attempt_repository, mock_order_repository) -> None:
        attempt = _make_attempt_mock(status="pending")
        mock_payment_attempt_repository.get_by_id.return_value = attempt
        mock_payment_attempt_repository.update.side_effect = lambda e: e
        service = PaymentAttemptService(mock_payment_attempt_repository, mock_order_repository)

        result = service.mark_as_success(1, "txn_123")

        assert result.status == "success"
        assert result.channel_transaction_id == "txn_123"

    def test_idempotent_already_success(self, mock_payment_attempt_repository, mock_order_repository) -> None:
        attempt = _make_attempt_mock(status="success", channel_transaction_id="txn_123")
        mock_payment_attempt_repository.get_by_id.return_value = attempt
        service = PaymentAttemptService(mock_payment_attempt_repository, mock_order_repository)

        result = service.mark_as_success(1, "txn_456")

        assert result.status == "success"
        assert result.channel_transaction_id == "txn_123"
        mock_payment_attempt_repository.update.assert_not_called()

    def test_invalid_from_failed(self, mock_payment_attempt_repository, mock_order_repository) -> None:
        attempt = _make_attempt_mock(status="failed")
        mock_payment_attempt_repository.get_by_id.return_value = attempt
        service = PaymentAttemptService(mock_payment_attempt_repository, mock_order_repository)

        with pytest.raises(ValueError, match="Invalid status transition"):
            service.mark_as_success(1, "txn_123")

    def test_not_found(self, mock_payment_attempt_repository, mock_order_repository) -> None:
        mock_payment_attempt_repository.get_by_id.return_value = None
        service = PaymentAttemptService(mock_payment_attempt_repository, mock_order_repository)

        assert service.mark_as_success(999, "txn_123") is None


class TestMarkAsFailed:
    def test_success_from_pending(self, mock_payment_attempt_repository, mock_order_repository) -> None:
        attempt = _make_attempt_mock(status="pending")
        mock_payment_attempt_repository.get_by_id.return_value = attempt
        mock_payment_attempt_repository.update.side_effect = lambda e: e
        service = PaymentAttemptService(mock_payment_attempt_repository, mock_order_repository)

        result = service.mark_as_failed(1)

        assert result.status == "failed"

    def test_idempotent_already_failed(self, mock_payment_attempt_repository, mock_order_repository) -> None:
        attempt = _make_attempt_mock(status="failed")
        mock_payment_attempt_repository.get_by_id.return_value = attempt
        service = PaymentAttemptService(mock_payment_attempt_repository, mock_order_repository)

        result = service.mark_as_failed(1)

        assert result.status == "failed"
        mock_payment_attempt_repository.update.assert_not_called()

    def test_invalid_from_success(self, mock_payment_attempt_repository, mock_order_repository) -> None:
        attempt = _make_attempt_mock(status="success")
        mock_payment_attempt_repository.get_by_id.return_value = attempt
        service = PaymentAttemptService(mock_payment_attempt_repository, mock_order_repository)

        with pytest.raises(ValueError, match="Invalid status transition"):
            service.mark_as_failed(1)

    def test_not_found(self, mock_payment_attempt_repository, mock_order_repository) -> None:
        mock_payment_attempt_repository.get_by_id.return_value = None
        service = PaymentAttemptService(mock_payment_attempt_repository, mock_order_repository)

        assert service.mark_as_failed(999) is None


class TestMarkSuccessAutoPayOrder:
    """mark_success 应自动将关联 Order 状态更新为 paid。"""

    def test_auto_pays_order(self, mock_payment_attempt_repository, mock_order_repository) -> None:
        attempt = _make_attempt_mock(status="pending", order_id=1)
        order = _make_order_mock(id=1, status="pending")
        mock_payment_attempt_repository.get_by_id.return_value = attempt
        mock_payment_attempt_repository.update.side_effect = lambda e: e
        mock_order_repository.get_by_id.return_value = order
        mock_order_repository.update.side_effect = lambda e: e

        service = PaymentAttemptService(mock_payment_attempt_repository, mock_order_repository)
        result = service.mark_as_success(1, "txn_auto_pay")

        assert result.status == "success"
        assert result.channel_transaction_id == "txn_auto_pay"
        # Verify order_repo.update was called and order.status set to paid
        mock_order_repository.update.assert_called_once()
        updated_order = mock_order_repository.update.call_args[0][0]
        assert updated_order.status == "paid"
        assert updated_order.paid_at is not None

    def test_order_already_paid_idempotent(
        self, mock_payment_attempt_repository, mock_order_repository
    ) -> None:
        attempt = _make_attempt_mock(status="pending", order_id=1)
        order = _make_order_mock(id=1, status="paid")
        mock_payment_attempt_repository.get_by_id.return_value = attempt
        mock_payment_attempt_repository.update.side_effect = lambda e: e
        mock_order_repository.get_by_id.return_value = order
        mock_order_repository.update.side_effect = lambda e: e

        service = PaymentAttemptService(mock_payment_attempt_repository, mock_order_repository)
        result = service.mark_as_success(1, "txn_idem")

        assert result.status == "success"
        # order already paid — no need to call update (idempotent)
        mock_order_repository.update.assert_not_called()

    def test_order_not_found_still_marks_success(
        self, mock_payment_attempt_repository, mock_order_repository
    ) -> None:
        attempt = _make_attempt_mock(status="pending", order_id=1)
        mock_payment_attempt_repository.get_by_id.return_value = attempt
        mock_payment_attempt_repository.update.side_effect = lambda e: e
        mock_order_repository.get_by_id.return_value = None

        service = PaymentAttemptService(mock_payment_attempt_repository, mock_order_repository)
        result = service.mark_as_success(1, "txn_no_order")

        assert result.status == "success"
        assert result.channel_transaction_id == "txn_no_order"
        # order_repo.update should NOT be called (order not found)
        mock_order_repository.update.assert_not_called()

    def test_order_repo_call_args(
        self, mock_payment_attempt_repository, mock_order_repository
    ) -> None:
        attempt = _make_attempt_mock(status="pending", order_id=42)
        order = _make_order_mock(id=42, status="pending")
        mock_payment_attempt_repository.get_by_id.return_value = attempt
        mock_payment_attempt_repository.update.side_effect = lambda e: e
        mock_order_repository.get_by_id.return_value = order
        mock_order_repository.update.side_effect = lambda e: e

        service = PaymentAttemptService(mock_payment_attempt_repository, mock_order_repository)
        service.mark_as_success(1, "txn_verify_args")

        # Verify order is looked up by attempt.order_id
        mock_order_repository.get_by_id.assert_called_once_with(42)
        mock_order_repository.update.assert_called_once()
        updated_order = mock_order_repository.update.call_args[0][0]
        assert updated_order.id == 42
        assert updated_order.status == "paid"

    def test_attempt_already_success_skips_order_update(
        self, mock_payment_attempt_repository, mock_order_repository
    ) -> None:
        attempt = _make_attempt_mock(status="success", channel_transaction_id="txn_old")
        mock_payment_attempt_repository.get_by_id.return_value = attempt

        service = PaymentAttemptService(mock_payment_attempt_repository, mock_order_repository)
        result = service.mark_as_success(1, "txn_new")

        assert result.status == "success"
        assert result.channel_transaction_id == "txn_old"
        # attempt already success: no repo calls at all
        mock_payment_attempt_repository.update.assert_not_called()
        mock_order_repository.get_by_id.assert_not_called()
        mock_order_repository.update.assert_not_called()

    def test_order_canceled_does_not_raise(
        self, mock_payment_attempt_repository, mock_order_repository
    ) -> None:
        """When order is canceled, auto-pay should not raise (skip silently)."""
        attempt = _make_attempt_mock(status="pending", order_id=1)
        order = _make_order_mock(id=1, status="canceled")
        mock_payment_attempt_repository.get_by_id.return_value = attempt
        mock_payment_attempt_repository.update.side_effect = lambda e: e
        mock_order_repository.get_by_id.return_value = order
        mock_order_repository.update.side_effect = lambda e: e

        service = PaymentAttemptService(mock_payment_attempt_repository, mock_order_repository)
        result = service.mark_as_success(1, "txn_canceled_order")

        assert result.status == "success"
        # Order is canceled, implementation should skip order update
        mock_order_repository.update.assert_not_called()


class TestListFiltered:
    def test_delegates_to_repo(self, mock_payment_attempt_repository, mock_order_repository) -> None:
        attempts = [_make_attempt_mock()]
        mock_payment_attempt_repository.list_filtered.return_value = attempts
        service = PaymentAttemptService(mock_payment_attempt_repository, mock_order_repository)

        result = service.list_filtered(order_id=1, channel="alipay", status="pending")

        assert result == attempts
        mock_payment_attempt_repository.list_filtered.assert_called_once_with(
            order_id=1, channel="alipay", status="pending"
        )
