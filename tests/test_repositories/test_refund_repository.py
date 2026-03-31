"""Tests for RefundRepository."""

import pytest

from app.models.order import Order
from app.models.refund import Refund
from app.repositories.base import BaseRepository


def _insert_order(db_session) -> Order:
    repo = BaseRepository(Order, db_session)
    return repo.create(Order(external_user_id="user_001", type="one_time", amount=3000, status="paid"))


def _build_refund(order_id: int, **overrides) -> Refund:
    defaults = {
        "order_id": order_id,
        "amount": 3000,
        "reason": "用户申请退款",
        "status": "pending",
        "channel": "alipay",
    }
    defaults.update(overrides)
    return Refund(**defaults)


class TestRefundRepositoryCreate:
    def test_create_basic(self, refund_repository, db_session) -> None:
        order = _insert_order(db_session)
        refund = refund_repository.create(_build_refund(order_id=order.id))
        assert refund.id is not None
        assert refund.order_id == order.id
        assert refund.amount == 3000
        assert refund.reason == "用户申请退款"
        assert refund.status == "pending"
        assert refund.channel == "alipay"
        assert refund.channel_refund_id is None
        assert refund.completed_at is None
        assert refund.created_at is not None

    def test_create_with_all_channels(self, refund_repository, db_session) -> None:
        order = _insert_order(db_session)
        for channel in ("alipay", "wechat", "stripe"):
            refund = refund_repository.create(_build_refund(order_id=order.id, channel=channel))
            assert refund.channel == channel

    def test_create_with_reason(self, refund_repository, db_session) -> None:
        order = _insert_order(db_session)
        reasons = [
            "用户申请退款",
            "商品质量问题",
            "发货延迟",
            "误操作",
        ]
        for reason in reasons:
            refund = refund_repository.create(_build_refund(order_id=order.id, reason=reason))
            assert refund.reason == reason


class TestRefundRepositoryGetById:
    def test_get_by_id_found(self, refund_repository, db_session) -> None:
        order = _insert_order(db_session)
        created = refund_repository.create(_build_refund(order_id=order.id))
        result = refund_repository.get_by_id(created.id)
        assert result is not None
        assert result.id == created.id

    def test_get_by_id_not_found(self, refund_repository) -> None:
        assert refund_repository.get_by_id(999) is None


class TestRefundRepositoryGetByOrderId:
    def test_returns_refunds_for_order(self, refund_repository, db_session) -> None:
        order = _insert_order(db_session)
        refund_repository.create(_build_refund(order_id=order.id))
        refund_repository.create(_build_refund(order_id=order.id))

        result = refund_repository.get_by_order_id(order.id)
        assert len(result) == 2

    def test_returns_empty_for_nonexistent_order(self, refund_repository) -> None:
        assert refund_repository.get_by_order_id(999) == []

    def test_filters_by_order(self, refund_repository, db_session) -> None:
        order1 = _insert_order(db_session)
        order2 = _insert_order(db_session)
        refund_repository.create(_build_refund(order_id=order1.id))
        refund_repository.create(_build_refund(order_id=order2.id))

        result = refund_repository.get_by_order_id(order1.id)
        assert len(result) == 1
        assert result[0].order_id == order1.id

    def test_results_ordered_by_id(self, refund_repository, db_session) -> None:
        order = _insert_order(db_session)
        refund_repository.create(_build_refund(order_id=order.id))
        refund_repository.create(_build_refund(order_id=order.id))

        result = refund_repository.get_by_order_id(order.id)
        assert result[0].id < result[1].id


class TestRefundRepositoryListFiltered:
    def test_no_filters_returns_all(self, refund_repository, db_session) -> None:
        order = _insert_order(db_session)
        refund_repository.create(_build_refund(order_id=order.id))
        refund_repository.create(_build_refund(order_id=order.id))

        result = refund_repository.list_filtered()
        assert len(result) == 2

    def test_filter_by_order_id(self, refund_repository, db_session) -> None:
        order1 = _insert_order(db_session)
        order2 = _insert_order(db_session)
        refund_repository.create(_build_refund(order_id=order1.id))
        refund_repository.create(_build_refund(order_id=order2.id))

        result = refund_repository.list_filtered(order_id=order1.id)
        assert len(result) == 1
        assert result[0].order_id == order1.id

    def test_filter_by_status(self, refund_repository, db_session) -> None:
        order = _insert_order(db_session)
        refund_repository.create(_build_refund(order_id=order.id, status="pending"))
        refund_repository.create(_build_refund(order_id=order.id, status="success"))

        result = refund_repository.list_filtered(status="pending")
        assert len(result) == 1
        assert result[0].status == "pending"

    def test_filter_by_channel(self, refund_repository, db_session) -> None:
        order = _insert_order(db_session)
        refund_repository.create(_build_refund(order_id=order.id, channel="alipay"))
        refund_repository.create(_build_refund(order_id=order.id, channel="wechat"))

        result = refund_repository.list_filtered(channel="alipay")
        assert len(result) == 1
        assert result[0].channel == "alipay"

    def test_combined_filters(self, refund_repository, db_session) -> None:
        order = _insert_order(db_session)
        refund_repository.create(_build_refund(order_id=order.id, status="pending", channel="alipay"))
        refund_repository.create(_build_refund(order_id=order.id, status="success", channel="alipay"))
        refund_repository.create(_build_refund(order_id=order.id, status="pending", channel="wechat"))

        result = refund_repository.list_filtered(status="pending", channel="alipay")
        assert len(result) == 1
        assert result[0].status == "pending"
        assert result[0].channel == "alipay"

    def test_ordered_by_id_desc(self, refund_repository, db_session) -> None:
        order = _insert_order(db_session)
        refund_repository.create(_build_refund(order_id=order.id))
        second = refund_repository.create(_build_refund(order_id=order.id))

        result = refund_repository.list_filtered()
        assert result[0].id > result[1].id
        assert result[0].id == second.id


class TestRefundRepositoryListAll:
    def test_list_all_empty(self, refund_repository) -> None:
        assert refund_repository.list_all() == []

    def test_list_all_with_data(self, refund_repository, db_session) -> None:
        order = _insert_order(db_session)
        refund_repository.create(_build_refund(order_id=order.id))
        refund_repository.create(_build_refund(order_id=order.id))

        assert len(refund_repository.list_all()) == 2


class TestRefundRepositoryUpdate:
    def test_update_status(self, refund_repository, db_session) -> None:
        order = _insert_order(db_session)
        refund = refund_repository.create(_build_refund(order_id=order.id))
        refund.status = "success"
        updated = refund_repository.update(refund)
        assert updated.status == "success"

    def test_update_channel_refund_id(self, refund_repository, db_session) -> None:
        order = _insert_order(db_session)
        refund = refund_repository.create(_build_refund(order_id=order.id))
        refund.channel_refund_id = "refund_12345"
        updated = refund_repository.update(refund)
        assert updated.channel_refund_id == "refund_12345"

    def test_update_completed_at(self, refund_repository, db_session) -> None:
        from datetime import UTC, datetime

        order = _insert_order(db_session)
        refund = refund_repository.create(_build_refund(order_id=order.id))
        completed_time = datetime.now(UTC)
        refund.completed_at = completed_time
        updated = refund_repository.update(refund)
        assert updated.completed_at is not None
        # SQLite loses timezone info, compare datetime only
        assert (
            updated.completed_at.replace(microsecond=0, tzinfo=None)
            == completed_time.replace(microsecond=0, tzinfo=None)
        )

    def test_update_multiple_fields(self, refund_repository, db_session) -> None:
        from datetime import UTC, datetime

        order = _insert_order(db_session)
        refund = refund_repository.create(_build_refund(order_id=order.id))
        refund.status = "success"
        refund.channel_refund_id = "refund_12345"
        refund.completed_at = datetime.now(UTC)
        updated = refund_repository.update(refund)
        assert updated.status == "success"
        assert updated.channel_refund_id == "refund_12345"
        assert updated.completed_at is not None


class TestRefundRepositoryDelete:
    def test_delete_refund(self, refund_repository, db_session) -> None:
        order = _insert_order(db_session)
        refund = refund_repository.create(_build_refund(order_id=order.id))
        refund_repository.delete(refund)
        assert refund_repository.get_by_id(refund.id) is None


class TestRefundRepositoryFKConstraints:
    def test_create_with_invalid_order_id_raises_integrity_error(self, refund_repository) -> None:
        from sqlalchemy.exc import IntegrityError

        refund = _build_refund(order_id=99999)  # Non-existent order_id
        with pytest.raises(IntegrityError):
            refund_repository.create(refund)


class TestRefundRepositoryStatusTransitions:
    def test_pending_to_success(self, refund_repository, db_session) -> None:
        order = _insert_order(db_session)
        refund = refund_repository.create(_build_refund(order_id=order.id, status="pending"))
        refund.status = "success"
        updated = refund_repository.update(refund)
        assert updated.status == "success"

    def test_pending_to_failed(self, refund_repository, db_session) -> None:
        order = _insert_order(db_session)
        refund = refund_repository.create(_build_refund(order_id=order.id, status="pending"))
        refund.status = "failed"
        updated = refund_repository.update(refund)
        assert updated.status == "failed"


class TestRefundRepositoryDifferentAmounts:
    def test_create_with_various_amounts(self, refund_repository, db_session) -> None:
        order = _insert_order(db_session)
        amounts = [100, 1000, 3000, 5000, 10000]
        for amount in amounts:
            refund = refund_repository.create(_build_refund(order_id=order.id, amount=amount))
            assert refund.amount == amount

    def test_create_zero_amount(self, refund_repository, db_session) -> None:
        order = _insert_order(db_session)
        refund = refund_repository.create(_build_refund(order_id=order.id, amount=0))
        assert refund.amount == 0


class TestRefundRepositoryGetTotalRefundedAmount:
    def test_returns_zero_when_no_refunds(self, refund_repository, db_session) -> None:
        order = _insert_order(db_session)
        result = refund_repository.get_total_refunded_amount(order.id)
        assert result == 0

    def test_returns_zero_when_no_refunds_for_order(self, refund_repository, db_session) -> None:
        order1 = _insert_order(db_session)
        order2 = _insert_order(db_session)
        refund_repository.create(_build_refund(order_id=order1.id, amount=1000))
        result = refund_repository.get_total_refunded_amount(order2.id)
        assert result == 0

    def test_sums_pending_and_success_only(self, refund_repository, db_session) -> None:
        order = _insert_order(db_session)
        refund_repository.create(_build_refund(order_id=order.id, amount=1000, status="pending"))
        refund_repository.create(_build_refund(order_id=order.id, amount=1500, status="success"))
        refund_repository.create(_build_refund(order_id=order.id, amount=500, status="failed"))
        result = refund_repository.get_total_refunded_amount(order.id)
        assert result == 2500

    def test_excludes_failed_refunds(self, refund_repository, db_session) -> None:
        order = _insert_order(db_session)
        refund_repository.create(_build_refund(order_id=order.id, amount=2000, status="failed"))
        result = refund_repository.get_total_refunded_amount(order.id)
        assert result == 0

    def test_sums_multiple_pending_refunds(self, refund_repository, db_session) -> None:
        order = _insert_order(db_session)
        refund_repository.create(_build_refund(order_id=order.id, amount=1000, status="pending"))
        refund_repository.create(_build_refund(order_id=order.id, amount=1500, status="pending"))
        result = refund_repository.get_total_refunded_amount(order.id)
        assert result == 2500

    def test_returns_int_type(self, refund_repository, db_session) -> None:
        order = _insert_order(db_session)
        refund_repository.create(_build_refund(order_id=order.id, amount=1000, status="pending"))
        result = refund_repository.get_total_refunded_amount(order.id)
        assert isinstance(result, int)
