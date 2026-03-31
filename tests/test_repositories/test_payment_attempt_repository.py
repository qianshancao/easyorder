"""Tests for PaymentAttemptRepository."""

import pytest

from app.models.order import Order
from app.models.payment_attempt import PaymentAttempt
from app.repositories.base import BaseRepository


def _insert_order(db_session) -> Order:
    repo = BaseRepository(Order, db_session)
    return repo.create(Order(external_user_id="user_001", type="one_time", amount=3000, status="pending"))


def _build_attempt(order_id: int, **overrides) -> PaymentAttempt:
    defaults = {
        "order_id": order_id,
        "channel": "alipay",
        "amount": 3000,
        "status": "pending",
    }
    defaults.update(overrides)
    return PaymentAttempt(**defaults)


class TestPaymentAttemptRepositoryCreate:
    def test_create_basic(self, payment_attempt_repository, db_session) -> None:
        order = _insert_order(db_session)
        attempt = payment_attempt_repository.create(_build_attempt(order_id=order.id))
        assert attempt.id is not None
        assert attempt.order_id == order.id
        assert attempt.channel == "alipay"
        assert attempt.amount == 3000
        assert attempt.status == "pending"
        assert attempt.channel_transaction_id is None
        assert attempt.created_at is not None

    def test_create_with_all_channels(self, payment_attempt_repository, db_session) -> None:
        order = _insert_order(db_session)
        for channel in ("alipay", "wechat", "stripe"):
            attempt = payment_attempt_repository.create(_build_attempt(order_id=order.id, channel=channel))
            assert attempt.channel == channel


class TestPaymentAttemptRepositoryGetById:
    def test_get_by_id_found(self, payment_attempt_repository, db_session) -> None:
        order = _insert_order(db_session)
        created = payment_attempt_repository.create(_build_attempt(order_id=order.id))
        result = payment_attempt_repository.get_by_id(created.id)
        assert result is not None
        assert result.id == created.id

    def test_get_by_id_not_found(self, payment_attempt_repository) -> None:
        assert payment_attempt_repository.get_by_id(999) is None


class TestPaymentAttemptRepositoryGetByOrderId:
    def test_returns_attempts_for_order(self, payment_attempt_repository, db_session) -> None:
        order = _insert_order(db_session)
        payment_attempt_repository.create(_build_attempt(order_id=order.id))
        payment_attempt_repository.create(_build_attempt(order_id=order.id))

        result = payment_attempt_repository.get_by_order_id(order.id)
        assert len(result) == 2

    def test_returns_empty_for_nonexistent_order(self, payment_attempt_repository) -> None:
        assert payment_attempt_repository.get_by_order_id(999) == []

    def test_filters_by_order(self, payment_attempt_repository, db_session) -> None:
        order1 = _insert_order(db_session)
        order2 = _insert_order(db_session)
        payment_attempt_repository.create(_build_attempt(order_id=order1.id))
        payment_attempt_repository.create(_build_attempt(order_id=order2.id))

        result = payment_attempt_repository.get_by_order_id(order1.id)
        assert len(result) == 1
        assert result[0].order_id == order1.id

    def test_results_ordered_by_id(self, payment_attempt_repository, db_session) -> None:
        order = _insert_order(db_session)
        payment_attempt_repository.create(_build_attempt(order_id=order.id))
        payment_attempt_repository.create(_build_attempt(order_id=order.id))

        result = payment_attempt_repository.get_by_order_id(order.id)
        assert result[0].id < result[1].id


class TestPaymentAttemptRepositoryGetPendingByOrderId:
    def test_returns_pending_attempt(self, payment_attempt_repository, db_session) -> None:
        order = _insert_order(db_session)
        payment_attempt_repository.create(_build_attempt(order_id=order.id, status="pending"))

        result = payment_attempt_repository.get_pending_by_order_id(order.id)
        assert result is not None
        assert result.status == "pending"

    def test_returns_none_when_no_pending(self, payment_attempt_repository, db_session) -> None:
        order = _insert_order(db_session)

        result = payment_attempt_repository.get_pending_by_order_id(order.id)
        assert result is None

    def test_returns_none_when_all_resolved(self, payment_attempt_repository, db_session) -> None:
        order = _insert_order(db_session)
        payment_attempt_repository.create(_build_attempt(order_id=order.id, status="success"))
        payment_attempt_repository.create(_build_attempt(order_id=order.id, status="failed"))

        result = payment_attempt_repository.get_pending_by_order_id(order.id)
        assert result is None


class TestPaymentAttemptRepositoryListFiltered:
    def test_no_filters_returns_all(self, payment_attempt_repository, db_session) -> None:
        order = _insert_order(db_session)
        payment_attempt_repository.create(_build_attempt(order_id=order.id))
        payment_attempt_repository.create(_build_attempt(order_id=order.id))

        result = payment_attempt_repository.list_filtered()
        assert len(result) == 2

    def test_filter_by_order_id(self, payment_attempt_repository, db_session) -> None:
        order1 = _insert_order(db_session)
        order2 = _insert_order(db_session)
        payment_attempt_repository.create(_build_attempt(order_id=order1.id))
        payment_attempt_repository.create(_build_attempt(order_id=order2.id))

        result = payment_attempt_repository.list_filtered(order_id=order1.id)
        assert len(result) == 1
        assert result[0].order_id == order1.id

    def test_filter_by_channel(self, payment_attempt_repository, db_session) -> None:
        order = _insert_order(db_session)
        payment_attempt_repository.create(_build_attempt(order_id=order.id, channel="alipay"))
        payment_attempt_repository.create(_build_attempt(order_id=order.id, channel="wechat"))

        result = payment_attempt_repository.list_filtered(channel="alipay")
        assert len(result) == 1
        assert result[0].channel == "alipay"

    def test_filter_by_status(self, payment_attempt_repository, db_session) -> None:
        order = _insert_order(db_session)
        payment_attempt_repository.create(_build_attempt(order_id=order.id, status="pending"))
        payment_attempt_repository.create(_build_attempt(order_id=order.id, status="success"))

        result = payment_attempt_repository.list_filtered(status="pending")
        assert len(result) == 1
        assert result[0].status == "pending"

    def test_combined_filters(self, payment_attempt_repository, db_session) -> None:
        order = _insert_order(db_session)
        payment_attempt_repository.create(_build_attempt(order_id=order.id, channel="alipay", status="pending"))
        payment_attempt_repository.create(_build_attempt(order_id=order.id, channel="alipay", status="success"))
        payment_attempt_repository.create(_build_attempt(order_id=order.id, channel="wechat", status="pending"))

        result = payment_attempt_repository.list_filtered(channel="alipay", status="pending")
        assert len(result) == 1
        assert result[0].channel == "alipay"
        assert result[0].status == "pending"

    def test_ordered_by_id_desc(self, payment_attempt_repository, db_session) -> None:
        order = _insert_order(db_session)
        payment_attempt_repository.create(_build_attempt(order_id=order.id))
        second = payment_attempt_repository.create(_build_attempt(order_id=order.id))

        result = payment_attempt_repository.list_filtered()
        assert result[0].id > result[1].id
        assert result[0].id == second.id


class TestPaymentAttemptRepositoryListAll:
    def test_list_all_empty(self, payment_attempt_repository) -> None:
        assert payment_attempt_repository.list_all() == []

    def test_list_all_with_data(self, payment_attempt_repository, db_session) -> None:
        order = _insert_order(db_session)
        payment_attempt_repository.create(_build_attempt(order_id=order.id))
        payment_attempt_repository.create(_build_attempt(order_id=order.id))

        assert len(payment_attempt_repository.list_all()) == 2


class TestPaymentAttemptRepositoryUpdate:
    def test_update_status(self, payment_attempt_repository, db_session) -> None:
        order = _insert_order(db_session)
        attempt = payment_attempt_repository.create(_build_attempt(order_id=order.id))
        attempt.status = "success"
        updated = payment_attempt_repository.update(attempt)
        assert updated.status == "success"


class TestPaymentAttemptRepositoryDelete:
    def test_delete_attempt(self, payment_attempt_repository, db_session) -> None:
        order = _insert_order(db_session)
        attempt = payment_attempt_repository.create(_build_attempt(order_id=order.id))
        payment_attempt_repository.delete(attempt)
        assert payment_attempt_repository.get_by_id(attempt.id) is None


class TestPaymentAttemptRepositoryFKConstraints:
    def test_create_with_invalid_order_id_raises_integrity_error(self, payment_attempt_repository) -> None:
        from sqlalchemy.exc import IntegrityError

        attempt = _build_attempt(order_id=99999)  # Non-existent order_id
        with pytest.raises(IntegrityError):
            payment_attempt_repository.create(attempt)
