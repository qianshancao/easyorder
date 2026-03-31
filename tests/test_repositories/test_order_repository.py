"""Tests for OrderRepository."""

from datetime import UTC, datetime, timedelta

from app.models.order import Order
from app.models.plan import Plan
from app.models.subscription import Subscription
from app.repositories.base import BaseRepository


def _insert_plan(db_session) -> Plan:
    repo = BaseRepository(Plan, db_session)
    return repo.create(Plan(name="Basic", cycle="monthly", base_price=3000))


def _insert_subscription(db_session, plan_id: int, **overrides) -> Subscription:
    defaults = {
        "external_user_id": "user_001",
        "plan_id": plan_id,
        "plan_snapshot": {"name": "Basic", "cycle": "monthly", "base_price": 3000},
        "status": "active",
        "current_period_start": datetime.now(tz=UTC),
        "current_period_end": datetime.now(tz=UTC) + timedelta(days=30),
    }
    defaults.update(overrides)
    return BaseRepository(Subscription, db_session).create(Subscription(**defaults))


def _build_order(**overrides) -> Order:
    defaults = {
        "external_user_id": "user_001",
        "subscription_id": None,
        "type": "one_time",
        "amount": 3000,
        "currency": "CNY",
        "status": "pending",
    }
    defaults.update(overrides)
    return Order(**defaults)


class TestOrderRepositoryCreate:
    def test_create_one_time_order(self, order_repository, db_session) -> None:
        order = order_repository.create(_build_order())
        assert order.id is not None
        assert order.external_user_id == "user_001"
        assert order.type == "one_time"
        assert order.subscription_id is None
        assert order.amount == 3000
        assert order.currency == "CNY"
        assert order.status == "pending"
        assert order.paid_at is None
        assert order.canceled_at is None
        assert order.created_at is not None

    def test_create_with_subscription(self, order_repository, db_session) -> None:
        plan = _insert_plan(db_session)
        sub = _insert_subscription(db_session, plan.id)
        order = order_repository.create(
            _build_order(subscription_id=sub.id, type="opening", external_user_id="user_001")
        )
        assert order.subscription_id == sub.id
        assert order.type == "opening"


class TestOrderRepositoryGetById:
    def test_get_by_id_found(self, order_repository) -> None:
        created = order_repository.create(_build_order())
        result = order_repository.get_by_id(created.id)
        assert result is not None
        assert result.id == created.id

    def test_get_by_id_not_found(self, order_repository) -> None:
        assert order_repository.get_by_id(999) is None


class TestOrderRepositoryGetByExternalUserId:
    def test_returns_orders_for_user(self, order_repository) -> None:
        order_repository.create(_build_order(external_user_id="user_a"))
        order_repository.create(_build_order(external_user_id="user_a"))
        result = order_repository.get_by_external_user_id("user_a")
        assert len(result) == 2

    def test_returns_empty_for_nonexistent_user(self, order_repository) -> None:
        assert order_repository.get_by_external_user_id("nobody") == []

    def test_filters_by_user(self, order_repository) -> None:
        order_repository.create(_build_order(external_user_id="user_a"))
        order_repository.create(_build_order(external_user_id="user_b"))
        result = order_repository.get_by_external_user_id("user_a")
        assert len(result) == 1


class TestOrderRepositoryGetBySubscriptionId:
    def test_returns_orders_for_subscription(self, order_repository) -> None:
        order_repository.create(_build_order(subscription_id=1, type="opening"))
        order_repository.create(_build_order(subscription_id=1, type="renewal"))
        result = order_repository.get_by_subscription_id(1)
        assert len(result) == 2

    def test_returns_empty_for_nonexistent_subscription(self, order_repository) -> None:
        assert order_repository.get_by_subscription_id(999) == []


class TestOrderRepositoryListFiltered:
    def test_no_filters_returns_all(self, order_repository) -> None:
        order_repository.create(_build_order(external_user_id="user_a"))
        order_repository.create(_build_order(external_user_id="user_b"))
        assert len(order_repository.list_filtered()) == 2

    def test_filter_by_status(self, order_repository) -> None:
        order_repository.create(_build_order(status="pending"))
        order_repository.create(_build_order(status="paid"))
        result = order_repository.list_filtered(status="pending")
        assert len(result) == 1
        assert result[0].status == "pending"

    def test_filter_by_type(self, order_repository) -> None:
        order_repository.create(_build_order(type="one_time"))
        order_repository.create(_build_order(type="opening", subscription_id=1))
        result = order_repository.list_filtered(order_type="one_time")
        assert len(result) == 1
        assert result[0].type == "one_time"

    def test_filter_by_external_user_id(self, order_repository) -> None:
        order_repository.create(_build_order(external_user_id="user_a"))
        order_repository.create(_build_order(external_user_id="user_b"))
        result = order_repository.list_filtered(external_user_id="user_a")
        assert len(result) == 1

    def test_filter_by_subscription_id(self, order_repository) -> None:
        order_repository.create(_build_order(subscription_id=1, type="opening"))
        order_repository.create(_build_order(subscription_id=2, type="opening"))
        result = order_repository.list_filtered(subscription_id=1)
        assert len(result) == 1

    def test_combined_filters(self, order_repository) -> None:
        order_repository.create(_build_order(external_user_id="user_a", status="pending", type="one_time"))
        order_repository.create(_build_order(external_user_id="user_a", status="paid", type="one_time"))
        order_repository.create(_build_order(external_user_id="user_b", status="pending", type="one_time"))
        result = order_repository.list_filtered(external_user_id="user_a", status="pending")
        assert len(result) == 1

    def test_ordered_by_id_desc(self, order_repository) -> None:
        order_repository.create(_build_order(external_user_id="user_a"))
        order_repository.create(_build_order(external_user_id="user_b"))
        result = order_repository.list_filtered()
        assert result[0].id > result[1].id


class TestOrderRepositoryListAll:
    def test_list_all_empty(self, order_repository) -> None:
        assert order_repository.list_all() == []

    def test_list_all_with_data(self, order_repository) -> None:
        order_repository.create(_build_order(external_user_id="user_a"))
        order_repository.create(_build_order(external_user_id="user_b"))
        assert len(order_repository.list_all()) == 2
