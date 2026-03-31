"""Tests for OrderService."""

from datetime import UTC, datetime

import pytest

from app.schemas.order import OrderCreate
from app.services.order import OrderService

from .conftest import _make_order_mock, _make_subscription_mock


class TestCreateOrder:
    def test_create_one_time_order(self, mock_order_repository, mock_subscription_repository) -> None:
        mock_order_repository.create.side_effect = lambda e: e
        service = OrderService(mock_order_repository, mock_subscription_repository)

        result = service.create_order(OrderCreate(external_user_id="user_001", type="one_time", amount=3000))

        assert result.type == "one_time"
        assert result.subscription_id is None
        assert result.amount == 3000
        assert result.status == "pending"

    def test_create_one_time_with_subscription_id_raises(
        self, mock_order_repository, mock_subscription_repository
    ) -> None:
        service = OrderService(mock_order_repository, mock_subscription_repository)

        with pytest.raises(ValueError, match="subscription_id set to None"):
            service.create_order(
                OrderCreate(external_user_id="user_001", subscription_id=1, type="one_time", amount=3000)
            )

    def test_create_opening_order_with_subscription(self, mock_order_repository, mock_subscription_repository) -> None:
        sub = _make_subscription_mock()
        mock_subscription_repository.get_by_id.return_value = sub
        mock_order_repository.create.side_effect = lambda e: e
        service = OrderService(mock_order_repository, mock_subscription_repository)

        result = service.create_order(
            OrderCreate(external_user_id="user_001", subscription_id=1, type="opening", amount=3000)
        )

        assert result.type == "opening"
        assert result.subscription_id == 1

    def test_create_opening_without_subscription_raises(
        self, mock_order_repository, mock_subscription_repository
    ) -> None:
        service = OrderService(mock_order_repository, mock_subscription_repository)

        with pytest.raises(ValueError, match="requires subscription_id"):
            service.create_order(OrderCreate(external_user_id="user_001", type="opening", amount=3000))

    def test_create_subscription_order_subscription_not_found(
        self, mock_order_repository, mock_subscription_repository
    ) -> None:
        mock_subscription_repository.get_by_id.return_value = None
        service = OrderService(mock_order_repository, mock_subscription_repository)

        with pytest.raises(ValueError, match="not found"):
            service.create_order(
                OrderCreate(external_user_id="user_001", subscription_id=999, type="renewal", amount=3000)
            )


class TestGetOrder:
    def test_found(self, mock_order_repository, mock_subscription_repository) -> None:
        order = _make_order_mock()
        mock_order_repository.get_by_id.return_value = order
        service = OrderService(mock_order_repository, mock_subscription_repository)

        assert service.get_order(1) is order

    def test_not_found(self, mock_order_repository, mock_subscription_repository) -> None:
        mock_order_repository.get_by_id.return_value = None
        service = OrderService(mock_order_repository, mock_subscription_repository)

        assert service.get_order(999) is None


class TestListByExternalUserId:
    def test_returns_results(self, mock_order_repository, mock_subscription_repository) -> None:
        orders = [_make_order_mock(), _make_order_mock(id=2)]
        mock_order_repository.get_by_external_user_id.return_value = orders
        service = OrderService(mock_order_repository, mock_subscription_repository)

        result = service.list_by_external_user_id("user_001")
        assert len(result) == 2

    def test_empty(self, mock_order_repository, mock_subscription_repository) -> None:
        mock_order_repository.get_by_external_user_id.return_value = []
        service = OrderService(mock_order_repository, mock_subscription_repository)

        assert service.list_by_external_user_id("nobody") == []


class TestListBySubscriptionId:
    def test_returns_results(self, mock_order_repository, mock_subscription_repository) -> None:
        orders = [_make_order_mock(subscription_id=1, type="opening")]
        mock_order_repository.get_by_subscription_id.return_value = orders
        service = OrderService(mock_order_repository, mock_subscription_repository)

        result = service.list_by_subscription_id(1)
        assert len(result) == 1


class TestMarkAsPaid:
    def test_success_from_pending(self, mock_order_repository, mock_subscription_repository) -> None:
        order = _make_order_mock(status="pending")
        mock_order_repository.get_by_id.return_value = order
        mock_order_repository.update.side_effect = lambda e: e
        service = OrderService(mock_order_repository, mock_subscription_repository)

        result = service.mark_as_paid(1)
        assert result.status == "paid"
        assert result.paid_at is not None

    def test_idempotent_already_paid(self, mock_order_repository, mock_subscription_repository) -> None:
        order = _make_order_mock(status="paid", paid_at=datetime.now(tz=UTC))
        mock_order_repository.get_by_id.return_value = order
        service = OrderService(mock_order_repository, mock_subscription_repository)

        original_paid_at = order.paid_at
        result = service.mark_as_paid(1)
        assert result.status == "paid"
        assert result.paid_at == original_paid_at
        mock_order_repository.update.assert_not_called()

    def test_invalid_from_canceled(self, mock_order_repository, mock_subscription_repository) -> None:
        order = _make_order_mock(status="canceled")
        mock_order_repository.get_by_id.return_value = order
        service = OrderService(mock_order_repository, mock_subscription_repository)

        with pytest.raises(ValueError, match="Invalid status transition"):
            service.mark_as_paid(1)

    def test_not_found(self, mock_order_repository, mock_subscription_repository) -> None:
        mock_order_repository.get_by_id.return_value = None
        service = OrderService(mock_order_repository, mock_subscription_repository)

        assert service.mark_as_paid(999) is None


class TestMarkAsCanceled:
    def test_success_from_pending(self, mock_order_repository, mock_subscription_repository) -> None:
        order = _make_order_mock(status="pending")
        mock_order_repository.get_by_id.return_value = order
        mock_order_repository.update.side_effect = lambda e: e
        service = OrderService(mock_order_repository, mock_subscription_repository)

        result = service.mark_as_canceled(1)
        assert result.status == "canceled"
        assert result.canceled_at is not None

    def test_idempotent_already_canceled(self, mock_order_repository, mock_subscription_repository) -> None:
        order = _make_order_mock(status="canceled", canceled_at=datetime.now(tz=UTC))
        mock_order_repository.get_by_id.return_value = order
        service = OrderService(mock_order_repository, mock_subscription_repository)

        result = service.mark_as_canceled(1)
        assert result.status == "canceled"
        mock_order_repository.update.assert_not_called()

    def test_invalid_from_paid(self, mock_order_repository, mock_subscription_repository) -> None:
        order = _make_order_mock(status="paid", paid_at=datetime.now(tz=UTC))
        mock_order_repository.get_by_id.return_value = order
        service = OrderService(mock_order_repository, mock_subscription_repository)

        with pytest.raises(ValueError, match="Invalid status transition"):
            service.mark_as_canceled(1)

    def test_not_found(self, mock_order_repository, mock_subscription_repository) -> None:
        mock_order_repository.get_by_id.return_value = None
        service = OrderService(mock_order_repository, mock_subscription_repository)

        assert service.mark_as_canceled(999) is None


class TestListFiltered:
    def test_delegates_to_repo(self, mock_order_repository, mock_subscription_repository) -> None:
        orders = [_make_order_mock()]
        mock_order_repository.list_filtered.return_value = orders
        service = OrderService(mock_order_repository, mock_subscription_repository)

        result = service.list_filtered(status="pending", order_type="one_time")
        assert result == orders
        mock_order_repository.list_filtered.assert_called_once_with(
            external_user_id=None, subscription_id=None, status="pending", order_type="one_time"
        )
