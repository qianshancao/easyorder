"""Tests for PaymentTransactionRepository."""

import pytest

from app.models.order import Order
from app.models.payment_attempt import PaymentAttempt
from app.models.payment_transaction import PaymentTransaction
from app.repositories.base import BaseRepository


def _insert_order(db_session) -> Order:
    repo = BaseRepository(Order, db_session)
    return repo.create(Order(external_user_id="user_001", type="one_time", amount=3000, status="pending"))


def _insert_attempt(db_session, order_id: int) -> PaymentAttempt:
    repo = BaseRepository(PaymentAttempt, db_session)
    return repo.create(PaymentAttempt(order_id=order_id, channel="alipay", amount=3000, status="pending"))


def _build_transaction(payment_attempt_id: int, order_id: int, **overrides) -> PaymentTransaction:
    defaults = {
        "payment_attempt_id": payment_attempt_id,
        "order_id": order_id,
        "channel": "alipay",
        "amount": 3000,
        "currency": "CNY",
        "channel_transaction_id": "txn_001",
        "status": "confirmed",
    }
    defaults.update(overrides)
    return PaymentTransaction(**defaults)


class TestPaymentTransactionRepositoryCreate:
    def test_create_basic(self, payment_transaction_repository, db_session) -> None:
        order = _insert_order(db_session)
        attempt = _insert_attempt(db_session, order.id)
        txn = payment_transaction_repository.create(
            _build_transaction(payment_attempt_id=attempt.id, order_id=order.id)
        )
        assert txn.id is not None
        assert txn.payment_attempt_id == attempt.id
        assert txn.order_id == order.id
        assert txn.channel == "alipay"
        assert txn.amount == 3000
        assert txn.currency == "CNY"
        assert txn.channel_transaction_id == "txn_001"
        assert txn.status == "confirmed"
        assert txn.raw_callback_data is None
        assert txn.created_at is not None

    def test_create_with_raw_callback_data(self, payment_transaction_repository, db_session) -> None:
        order = _insert_order(db_session)
        attempt = _insert_attempt(db_session, order.id)
        txn = payment_transaction_repository.create(
            _build_transaction(
                payment_attempt_id=attempt.id,
                order_id=order.id,
                raw_callback_data='{"trade_no":"T123"}',
            )
        )
        assert txn.raw_callback_data == '{"trade_no":"T123"}'


class TestPaymentTransactionRepositoryGetById:
    def test_found(self, payment_transaction_repository, db_session) -> None:
        order = _insert_order(db_session)
        attempt = _insert_attempt(db_session, order.id)
        created = payment_transaction_repository.create(
            _build_transaction(payment_attempt_id=attempt.id, order_id=order.id)
        )
        result = payment_transaction_repository.get_by_id(created.id)
        assert result is not None
        assert result.id == created.id

    def test_not_found(self, payment_transaction_repository) -> None:
        assert payment_transaction_repository.get_by_id(999) is None


class TestPaymentTransactionRepositoryGetByPaymentAttemptId:
    def test_returns_transactions_for_attempt(self, payment_transaction_repository, db_session) -> None:
        order = _insert_order(db_session)
        attempt = _insert_attempt(db_session, order.id)
        payment_transaction_repository.create(
            _build_transaction(payment_attempt_id=attempt.id, order_id=order.id, channel_transaction_id="txn_1")
        )
        payment_transaction_repository.create(
            _build_transaction(payment_attempt_id=attempt.id, order_id=order.id, channel_transaction_id="txn_2")
        )
        result = payment_transaction_repository.get_by_payment_attempt_id(attempt.id)
        assert len(result) == 2

    def test_returns_empty_for_nonexistent(self, payment_transaction_repository) -> None:
        assert payment_transaction_repository.get_by_payment_attempt_id(999) == []

    def test_filters_by_attempt(self, payment_transaction_repository, db_session) -> None:
        order = _insert_order(db_session)
        attempt1 = _insert_attempt(db_session, order.id)
        attempt2 = _insert_attempt(db_session, order.id)
        payment_transaction_repository.create(_build_transaction(payment_attempt_id=attempt1.id, order_id=order.id))
        payment_transaction_repository.create(
            _build_transaction(payment_attempt_id=attempt2.id, order_id=order.id, channel_transaction_id="txn_other")
        )
        result = payment_transaction_repository.get_by_payment_attempt_id(attempt1.id)
        assert len(result) == 1
        assert result[0].payment_attempt_id == attempt1.id

    def test_ordered_by_id(self, payment_transaction_repository, db_session) -> None:
        order = _insert_order(db_session)
        attempt = _insert_attempt(db_session, order.id)
        payment_transaction_repository.create(
            _build_transaction(payment_attempt_id=attempt.id, order_id=order.id, channel_transaction_id="txn_a")
        )
        payment_transaction_repository.create(
            _build_transaction(payment_attempt_id=attempt.id, order_id=order.id, channel_transaction_id="txn_b")
        )
        result = payment_transaction_repository.get_by_payment_attempt_id(attempt.id)
        assert result[0].id < result[1].id


class TestPaymentTransactionRepositoryGetByOrderId:
    def test_returns_transactions_for_order(self, payment_transaction_repository, db_session) -> None:
        order = _insert_order(db_session)
        attempt = _insert_attempt(db_session, order.id)
        payment_transaction_repository.create(_build_transaction(payment_attempt_id=attempt.id, order_id=order.id))
        result = payment_transaction_repository.get_by_order_id(order.id)
        assert len(result) == 1

    def test_returns_empty_for_nonexistent(self, payment_transaction_repository) -> None:
        assert payment_transaction_repository.get_by_order_id(999) == []

    def test_ordered_by_id(self, payment_transaction_repository, db_session) -> None:
        order = _insert_order(db_session)
        attempt1 = _insert_attempt(db_session, order.id)
        attempt2 = _insert_attempt(db_session, order.id)
        payment_transaction_repository.create(
            _build_transaction(payment_attempt_id=attempt1.id, order_id=order.id, channel_transaction_id="txn_1")
        )
        payment_transaction_repository.create(
            _build_transaction(payment_attempt_id=attempt2.id, order_id=order.id, channel_transaction_id="txn_2")
        )
        result = payment_transaction_repository.get_by_order_id(order.id)
        assert result[0].id < result[1].id


class TestPaymentTransactionRepositoryGetByChannelTransactionId:
    def test_found(self, payment_transaction_repository, db_session) -> None:
        order = _insert_order(db_session)
        attempt = _insert_attempt(db_session, order.id)
        payment_transaction_repository.create(
            _build_transaction(
                payment_attempt_id=attempt.id, order_id=order.id, channel_transaction_id="unique_txn_123"
            )
        )
        result = payment_transaction_repository.get_by_channel_transaction_id("unique_txn_123")
        assert result is not None
        assert result.channel_transaction_id == "unique_txn_123"

    def test_not_found(self, payment_transaction_repository) -> None:
        result = payment_transaction_repository.get_by_channel_transaction_id("nonexistent")
        assert result is None


class TestPaymentTransactionRepositoryListFiltered:
    def test_no_filters_returns_all(self, payment_transaction_repository, db_session) -> None:
        order = _insert_order(db_session)
        attempt = _insert_attempt(db_session, order.id)
        payment_transaction_repository.create(
            _build_transaction(payment_attempt_id=attempt.id, order_id=order.id, channel_transaction_id="txn_1")
        )
        payment_transaction_repository.create(
            _build_transaction(payment_attempt_id=attempt.id, order_id=order.id, channel_transaction_id="txn_2")
        )
        result = payment_transaction_repository.list_filtered()
        assert len(result) == 2

    def test_filter_by_payment_attempt_id(self, payment_transaction_repository, db_session) -> None:
        order = _insert_order(db_session)
        attempt1 = _insert_attempt(db_session, order.id)
        attempt2 = _insert_attempt(db_session, order.id)
        payment_transaction_repository.create(_build_transaction(payment_attempt_id=attempt1.id, order_id=order.id))
        payment_transaction_repository.create(
            _build_transaction(payment_attempt_id=attempt2.id, order_id=order.id, channel_transaction_id="txn_b")
        )
        result = payment_transaction_repository.list_filtered(payment_attempt_id=attempt1.id)
        assert len(result) == 1
        assert result[0].payment_attempt_id == attempt1.id

    def test_filter_by_order_id(self, payment_transaction_repository, db_session) -> None:
        order1 = _insert_order(db_session)
        order2 = _insert_order(db_session)
        attempt1 = _insert_attempt(db_session, order1.id)
        attempt2 = _insert_attempt(db_session, order2.id)
        payment_transaction_repository.create(_build_transaction(payment_attempt_id=attempt1.id, order_id=order1.id))
        payment_transaction_repository.create(
            _build_transaction(payment_attempt_id=attempt2.id, order_id=order2.id, channel_transaction_id="txn_b")
        )
        result = payment_transaction_repository.list_filtered(order_id=order1.id)
        assert len(result) == 1
        assert result[0].order_id == order1.id

    def test_filter_by_channel(self, payment_transaction_repository, db_session) -> None:
        order = _insert_order(db_session)
        attempt = _insert_attempt(db_session, order.id)
        payment_transaction_repository.create(
            _build_transaction(payment_attempt_id=attempt.id, order_id=order.id, channel="alipay")
        )
        payment_transaction_repository.create(
            _build_transaction(
                payment_attempt_id=attempt.id, order_id=order.id, channel="wechat", channel_transaction_id="txn_w"
            )
        )
        result = payment_transaction_repository.list_filtered(channel="alipay")
        assert len(result) == 1
        assert result[0].channel == "alipay"

    def test_filter_by_status(self, payment_transaction_repository, db_session) -> None:
        order = _insert_order(db_session)
        attempt = _insert_attempt(db_session, order.id)
        payment_transaction_repository.create(
            _build_transaction(payment_attempt_id=attempt.id, order_id=order.id, status="confirmed")
        )
        payment_transaction_repository.create(
            _build_transaction(
                payment_attempt_id=attempt.id, order_id=order.id, status="refunded", channel_transaction_id="txn_r"
            )
        )
        result = payment_transaction_repository.list_filtered(status="confirmed")
        assert len(result) == 1
        assert result[0].status == "confirmed"

    def test_combined_filters(self, payment_transaction_repository, db_session) -> None:
        order = _insert_order(db_session)
        attempt = _insert_attempt(db_session, order.id)
        payment_transaction_repository.create(
            _build_transaction(payment_attempt_id=attempt.id, order_id=order.id, channel="alipay", status="confirmed")
        )
        payment_transaction_repository.create(
            _build_transaction(
                payment_attempt_id=attempt.id,
                order_id=order.id,
                channel="alipay",
                status="refunded",
                channel_transaction_id="txn_r",
            )
        )
        payment_transaction_repository.create(
            _build_transaction(
                payment_attempt_id=attempt.id,
                order_id=order.id,
                channel="wechat",
                status="confirmed",
                channel_transaction_id="txn_w",
            )
        )
        result = payment_transaction_repository.list_filtered(channel="alipay", status="confirmed")
        assert len(result) == 1
        assert result[0].channel == "alipay"
        assert result[0].status == "confirmed"

    def test_ordered_by_id_desc(self, payment_transaction_repository, db_session) -> None:
        order = _insert_order(db_session)
        attempt = _insert_attempt(db_session, order.id)
        payment_transaction_repository.create(
            _build_transaction(payment_attempt_id=attempt.id, order_id=order.id, channel_transaction_id="txn_1")
        )
        second = payment_transaction_repository.create(
            _build_transaction(payment_attempt_id=attempt.id, order_id=order.id, channel_transaction_id="txn_2")
        )
        result = payment_transaction_repository.list_filtered()
        assert result[0].id > result[1].id
        assert result[0].id == second.id


class TestPaymentTransactionRepositoryListAll:
    def test_empty(self, payment_transaction_repository) -> None:
        assert payment_transaction_repository.list_all() == []

    def test_with_data(self, payment_transaction_repository, db_session) -> None:
        order = _insert_order(db_session)
        attempt = _insert_attempt(db_session, order.id)
        payment_transaction_repository.create(_build_transaction(payment_attempt_id=attempt.id, order_id=order.id))
        payment_transaction_repository.create(
            _build_transaction(payment_attempt_id=attempt.id, order_id=order.id, channel_transaction_id="txn_2")
        )
        assert len(payment_transaction_repository.list_all()) == 2


class TestPaymentTransactionRepositoryUpdate:
    def test_update_status(self, payment_transaction_repository, db_session) -> None:
        order = _insert_order(db_session)
        attempt = _insert_attempt(db_session, order.id)
        txn = payment_transaction_repository.create(
            _build_transaction(payment_attempt_id=attempt.id, order_id=order.id)
        )
        txn.status = "refunded"
        updated = payment_transaction_repository.update(txn)
        assert updated.status == "refunded"


class TestPaymentTransactionRepositoryDelete:
    def test_delete(self, payment_transaction_repository, db_session) -> None:
        order = _insert_order(db_session)
        attempt = _insert_attempt(db_session, order.id)
        txn = payment_transaction_repository.create(
            _build_transaction(payment_attempt_id=attempt.id, order_id=order.id)
        )
        payment_transaction_repository.delete(txn)
        assert payment_transaction_repository.get_by_id(txn.id) is None


class TestPaymentTransactionRepositoryFKConstraints:
    def test_invalid_payment_attempt_id_raises(self, payment_transaction_repository, db_session) -> None:
        from sqlalchemy.exc import IntegrityError

        order = _insert_order(db_session)
        txn = _build_transaction(payment_attempt_id=99999, order_id=order.id)
        with pytest.raises(IntegrityError):
            payment_transaction_repository.create(txn)

    def test_invalid_order_id_raises(self, payment_transaction_repository, db_session) -> None:
        from sqlalchemy.exc import IntegrityError

        order = _insert_order(db_session)
        attempt = _insert_attempt(db_session, order.id)
        txn = _build_transaction(payment_attempt_id=attempt.id, order_id=99999)
        with pytest.raises(IntegrityError):
            payment_transaction_repository.create(txn)
