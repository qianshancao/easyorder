"""Tests for PaymentTransactionService."""

from app.schemas.payment_transaction import PaymentTransactionCreate
from app.services.payment_transaction import PaymentTransactionService

from .conftest import _make_payment_transaction_mock


class TestCreateTransaction:
    def test_create_success(self, mock_payment_transaction_repository) -> None:
        mock_payment_transaction_repository.get_by_channel_transaction_id.return_value = None
        mock_payment_transaction_repository.create.side_effect = lambda e: e

        service = PaymentTransactionService(mock_payment_transaction_repository)
        result = service.create_transaction(
            PaymentTransactionCreate(
                payment_attempt_id=1,
                order_id=1,
                channel="alipay",
                amount=3000,
                channel_transaction_id="txn_001",
            )
        )

        assert result.payment_attempt_id == 1
        assert result.order_id == 1
        assert result.channel == "alipay"
        assert result.amount == 3000
        assert result.channel_transaction_id == "txn_001"
        assert result.status == "confirmed"
        mock_payment_transaction_repository.create.assert_called_once()

    def test_create_idempotent(self, mock_payment_transaction_repository) -> None:
        existing = _make_payment_transaction_mock()
        mock_payment_transaction_repository.get_by_channel_transaction_id.return_value = existing

        service = PaymentTransactionService(mock_payment_transaction_repository)
        result = service.create_transaction(
            PaymentTransactionCreate(
                payment_attempt_id=1,
                order_id=1,
                channel="alipay",
                amount=3000,
                channel_transaction_id="txn_001",
            )
        )

        assert result.id == existing.id
        mock_payment_transaction_repository.create.assert_not_called()

    def test_create_with_raw_callback_data(self, mock_payment_transaction_repository) -> None:
        mock_payment_transaction_repository.get_by_channel_transaction_id.return_value = None
        mock_payment_transaction_repository.create.side_effect = lambda e: e

        service = PaymentTransactionService(mock_payment_transaction_repository)
        result = service.create_transaction(
            PaymentTransactionCreate(
                payment_attempt_id=1,
                order_id=1,
                channel="alipay",
                amount=3000,
                channel_transaction_id="txn_002",
                raw_callback_data='{"trade_no":"T123"}',
            )
        )

        assert result.raw_callback_data == '{"trade_no":"T123"}'


class TestGetTransaction:
    def test_found(self, mock_payment_transaction_repository) -> None:
        txn = _make_payment_transaction_mock()
        mock_payment_transaction_repository.get_by_id.return_value = txn

        service = PaymentTransactionService(mock_payment_transaction_repository)
        assert service.get_transaction(1) is txn

    def test_not_found(self, mock_payment_transaction_repository) -> None:
        mock_payment_transaction_repository.get_by_id.return_value = None

        service = PaymentTransactionService(mock_payment_transaction_repository)
        assert service.get_transaction(999) is None


class TestListByAttempt:
    def test_returns_results(self, mock_payment_transaction_repository) -> None:
        txns = [_make_payment_transaction_mock()]
        mock_payment_transaction_repository.get_by_payment_attempt_id.return_value = txns

        service = PaymentTransactionService(mock_payment_transaction_repository)
        result = service.list_by_attempt(1)
        assert len(result) == 1

    def test_empty(self, mock_payment_transaction_repository) -> None:
        mock_payment_transaction_repository.get_by_payment_attempt_id.return_value = []

        service = PaymentTransactionService(mock_payment_transaction_repository)
        assert service.list_by_attempt(999) == []


class TestListByOrder:
    def test_returns_results(self, mock_payment_transaction_repository) -> None:
        txns = [_make_payment_transaction_mock()]
        mock_payment_transaction_repository.get_by_order_id.return_value = txns

        service = PaymentTransactionService(mock_payment_transaction_repository)
        result = service.list_by_order(1)
        assert len(result) == 1

    def test_empty(self, mock_payment_transaction_repository) -> None:
        mock_payment_transaction_repository.get_by_order_id.return_value = []

        service = PaymentTransactionService(mock_payment_transaction_repository)
        assert service.list_by_order(999) == []


class TestListFiltered:
    def test_delegates_to_repo(self, mock_payment_transaction_repository) -> None:
        txns = [_make_payment_transaction_mock()]
        mock_payment_transaction_repository.list_filtered.return_value = txns

        service = PaymentTransactionService(mock_payment_transaction_repository)
        result = service.list_filtered(order_id=1, channel="alipay")

        assert result == txns
        mock_payment_transaction_repository.list_filtered.assert_called_once_with(
            order_id=1,
            channel="alipay",
            payment_attempt_id=None,
            status=None,
            limit=100,
            offset=0,
        )
