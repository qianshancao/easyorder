"""Tests for PaymentAttemptService."""

from datetime import UTC, datetime
from unittest.mock import MagicMock

import pytest

from app.models.order import Order
from app.models.payment_attempt import PaymentAttempt
from app.schemas.payment_attempt import PaymentAttemptCreate
from app.services.payment_attempt import PaymentAttemptService


def _make_attempt_mock(**overrides) -> MagicMock:
    defaults = {
        "id": 1,
        "order_id": 1,
        "channel": "alipay",
        "amount": 3000,
        "status": "pending",
        "channel_transaction_id": None,
        "created_at": datetime.now(tz=UTC),
    }
    defaults.update(overrides)
    mock = MagicMock(spec=PaymentAttempt)
    for k, v in defaults.items():
        setattr(mock, k, v)
    return mock


def _make_order_mock(**overrides) -> MagicMock:
    defaults = {
        "id": 1,
        "external_user_id": "user_001",
        "status": "pending",
    }
    defaults.update(overrides)
    mock = MagicMock(spec=Order)
    for k, v in defaults.items():
        setattr(mock, k, v)
    return mock


class TestCreateAttempt:
    def test_create_success(
        self, mock_payment_attempt_repository, mock_order_repository
    ) -> None:
        order = _make_order_mock()
        mock_order_repository.get_by_id.return_value = order
        mock_payment_attempt_repository.get_pending_by_order_id.return_value = None
        mock_payment_attempt_repository.create.side_effect = lambda e: e

        service = PaymentAttemptService(mock_payment_attempt_repository, mock_order_repository)

        result = service.create_attempt(
            PaymentAttemptCreate(order_id=1, channel="alipay", amount=3000)
        )

        assert result.order_id == 1
        assert result.channel == "alipay"
        assert result.amount == 3000
        assert result.status == "pending"

    def test_create_order_not_found(
        self, mock_payment_attempt_repository, mock_order_repository
    ) -> None:
        mock_order_repository.get_by_id.return_value = None
        service = PaymentAttemptService(mock_payment_attempt_repository, mock_order_repository)

        with pytest.raises(ValueError, match="Order 1 not found"):
            service.create_attempt(
                PaymentAttemptCreate(order_id=1, channel="alipay", amount=3000)
            )

    def test_create_idempotent_returns_existing_pending(
        self, mock_payment_attempt_repository, mock_order_repository
    ) -> None:
        order = _make_order_mock()
        existing = _make_attempt_mock()
        mock_order_repository.get_by_id.return_value = order
        mock_payment_attempt_repository.get_pending_by_order_id.return_value = existing

        service = PaymentAttemptService(mock_payment_attempt_repository, mock_order_repository)

        result = service.create_attempt(
            PaymentAttemptCreate(order_id=1, channel="alipay", amount=3000)
        )

        assert result.id == existing.id
        mock_payment_attempt_repository.create.assert_not_called()

    def test_create_allows_new_after_failed(
        self, mock_payment_attempt_repository, mock_order_repository
    ) -> None:
        order = _make_order_mock()
        new_attempt = _make_attempt_mock(id=2)
        mock_order_repository.get_by_id.return_value = order
        mock_payment_attempt_repository.get_pending_by_order_id.return_value = None
        mock_payment_attempt_repository.create.side_effect = lambda e: new_attempt

        service = PaymentAttemptService(mock_payment_attempt_repository, mock_order_repository)

        result = service.create_attempt(
            PaymentAttemptCreate(order_id=1, channel="alipay", amount=3000)
        )

        assert result.id == 2


class TestGetAttempt:
    def test_found(
        self, mock_payment_attempt_repository, mock_order_repository
    ) -> None:
        attempt = _make_attempt_mock()
        mock_payment_attempt_repository.get_by_id.return_value = attempt
        service = PaymentAttemptService(mock_payment_attempt_repository, mock_order_repository)

        assert service.get_attempt(1) is attempt

    def test_not_found(
        self, mock_payment_attempt_repository, mock_order_repository
    ) -> None:
        mock_payment_attempt_repository.get_by_id.return_value = None
        service = PaymentAttemptService(mock_payment_attempt_repository, mock_order_repository)

        assert service.get_attempt(999) is None


class TestListByOrder:
    def test_returns_results(
        self, mock_payment_attempt_repository, mock_order_repository
    ) -> None:
        attempts = [_make_attempt_mock(), _make_attempt_mock(id=2)]
        mock_payment_attempt_repository.get_by_order_id.return_value = attempts
        service = PaymentAttemptService(mock_payment_attempt_repository, mock_order_repository)

        result = service.list_by_order(1)
        assert len(result) == 2

    def test_empty(
        self, mock_payment_attempt_repository, mock_order_repository
    ) -> None:
        mock_payment_attempt_repository.get_by_order_id.return_value = []
        service = PaymentAttemptService(mock_payment_attempt_repository, mock_order_repository)

        assert service.list_by_order(999) == []


class TestMarkAsSuccess:
    def test_success_from_pending(
        self, mock_payment_attempt_repository, mock_order_repository
    ) -> None:
        attempt = _make_attempt_mock(status="pending")
        mock_payment_attempt_repository.get_by_id.return_value = attempt
        mock_payment_attempt_repository.update.side_effect = lambda e: e
        service = PaymentAttemptService(mock_payment_attempt_repository, mock_order_repository)

        result = service.mark_as_success(1, "txn_123")

        assert result.status == "success"
        assert result.channel_transaction_id == "txn_123"

    def test_idempotent_already_success(
        self, mock_payment_attempt_repository, mock_order_repository
    ) -> None:
        attempt = _make_attempt_mock(status="success", channel_transaction_id="txn_123")
        mock_payment_attempt_repository.get_by_id.return_value = attempt
        service = PaymentAttemptService(mock_payment_attempt_repository, mock_order_repository)

        result = service.mark_as_success(1, "txn_456")

        assert result.status == "success"
        mock_payment_attempt_repository.update.assert_not_called()

    def test_invalid_from_failed(
        self, mock_payment_attempt_repository, mock_order_repository
    ) -> None:
        attempt = _make_attempt_mock(status="failed")
        mock_payment_attempt_repository.get_by_id.return_value = attempt
        service = PaymentAttemptService(mock_payment_attempt_repository, mock_order_repository)

        with pytest.raises(ValueError, match="Invalid status transition"):
            service.mark_as_success(1, "txn_123")

    def test_not_found(
        self, mock_payment_attempt_repository, mock_order_repository
    ) -> None:
        mock_payment_attempt_repository.get_by_id.return_value = None
        service = PaymentAttemptService(mock_payment_attempt_repository, mock_order_repository)

        assert service.mark_as_success(999, "txn_123") is None


class TestMarkAsFailed:
    def test_success_from_pending(
        self, mock_payment_attempt_repository, mock_order_repository
    ) -> None:
        attempt = _make_attempt_mock(status="pending")
        mock_payment_attempt_repository.get_by_id.return_value = attempt
        mock_payment_attempt_repository.update.side_effect = lambda e: e
        service = PaymentAttemptService(mock_payment_attempt_repository, mock_order_repository)

        result = service.mark_as_failed(1)

        assert result.status == "failed"

    def test_idempotent_already_failed(
        self, mock_payment_attempt_repository, mock_order_repository
    ) -> None:
        attempt = _make_attempt_mock(status="failed")
        mock_payment_attempt_repository.get_by_id.return_value = attempt
        service = PaymentAttemptService(mock_payment_attempt_repository, mock_order_repository)

        result = service.mark_as_failed(1)

        assert result.status == "failed"
        mock_payment_attempt_repository.update.assert_not_called()

    def test_invalid_from_success(
        self, mock_payment_attempt_repository, mock_order_repository
    ) -> None:
        attempt = _make_attempt_mock(status="success")
        mock_payment_attempt_repository.get_by_id.return_value = attempt
        service = PaymentAttemptService(mock_payment_attempt_repository, mock_order_repository)

        with pytest.raises(ValueError, match="Invalid status transition"):
            service.mark_as_failed(1)

    def test_not_found(
        self, mock_payment_attempt_repository, mock_order_repository
    ) -> None:
        mock_payment_attempt_repository.get_by_id.return_value = None
        service = PaymentAttemptService(mock_payment_attempt_repository, mock_order_repository)

        assert service.mark_as_failed(999) is None


class TestListFiltered:
    def test_delegates_to_repo(
        self, mock_payment_attempt_repository, mock_order_repository
    ) -> None:
        attempts = [_make_attempt_mock()]
        mock_payment_attempt_repository.list_filtered.return_value = attempts
        service = PaymentAttemptService(mock_payment_attempt_repository, mock_order_repository)

        result = service.list_filtered(order_id=1, channel="alipay", status="pending")

        assert result == attempts
        mock_payment_attempt_repository.list_filtered.assert_called_once_with(
            order_id=1, channel="alipay", status="pending"
        )
