"""Tests for SubscriptionRepository."""

from datetime import UTC, datetime, timedelta

import pytest

from app.models.plan import Plan
from app.models.subscription import Subscription
from app.repositories.base import BaseRepository


def _insert_plan(db_session) -> Plan:
    """Helper: insert a Plan row for FK constraint."""
    repo = BaseRepository(Plan, db_session)
    return repo.create(Plan(name="Basic", cycle="monthly", base_price=3000))


def _build_subscription(plan_id: int, **overrides) -> Subscription:
    defaults = {
        "external_user_id": "user_001",
        "plan_id": plan_id,
        "plan_snapshot": {"name": "Basic", "cycle": "monthly", "base_price": 3000},
        "status": "trial",
        "current_period_start": datetime.now(tz=UTC),
        "current_period_end": datetime.now(tz=UTC) + timedelta(days=7),
    }
    defaults.update(overrides)
    return Subscription(**defaults)


class TestSubscriptionRepositoryCreate:
    def test_create_subscription_success(self, subscription_repository, db_session) -> None:
        plan = _insert_plan(db_session)
        sub = subscription_repository.create(_build_subscription(plan.id))
        assert sub.id is not None
        assert sub.external_user_id == "user_001"
        assert sub.plan_id == plan.id
        assert sub.status == "trial"
        assert sub.plan_snapshot == {"name": "Basic", "cycle": "monthly", "base_price": 3000}
        assert sub.canceled_at is None
        assert sub.created_at is not None

    def test_create_with_different_status(self, subscription_repository, db_session) -> None:
        plan = _insert_plan(db_session)
        sub = subscription_repository.create(_build_subscription(plan.id, status="active"))
        assert sub.status == "active"


class TestSubscriptionRepositoryGetById:
    def test_get_by_id_found(self, subscription_repository, db_session) -> None:
        plan = _insert_plan(db_session)
        sub = subscription_repository.create(_build_subscription(plan.id))
        result = subscription_repository.get_by_id(sub.id)
        assert result is not None
        assert result.external_user_id == "user_001"

    def test_get_by_id_not_found(self, subscription_repository) -> None:
        assert subscription_repository.get_by_id(999) is None


class TestSubscriptionRepositoryGetByExternalUserId:
    def test_returns_subscriptions_for_user(self, subscription_repository, db_session) -> None:
        plan = _insert_plan(db_session)
        subscription_repository.create(_build_subscription(plan.id, external_user_id="user_a"))
        subscription_repository.create(_build_subscription(plan.id, external_user_id="user_a"))
        result = subscription_repository.get_by_external_user_id("user_a")
        assert len(result) == 2

    def test_returns_empty_for_nonexistent_user(self, subscription_repository) -> None:
        result = subscription_repository.get_by_external_user_id("nobody")
        assert result == []

    def test_filters_by_user(self, subscription_repository, db_session) -> None:
        plan = _insert_plan(db_session)
        subscription_repository.create(_build_subscription(plan.id, external_user_id="user_a"))
        subscription_repository.create(_build_subscription(plan.id, external_user_id="user_b"))
        result = subscription_repository.get_by_external_user_id("user_a")
        assert len(result) == 1
        assert result[0].external_user_id == "user_a"

    def test_results_ordered_by_id(self, subscription_repository, db_session) -> None:
        plan = _insert_plan(db_session)
        subscription_repository.create(_build_subscription(plan.id, external_user_id="user_a"))
        subscription_repository.create(_build_subscription(plan.id, external_user_id="user_a"))
        result = subscription_repository.get_by_external_user_id("user_a")
        assert result[0].id < result[1].id


class TestSubscriptionRepositoryListAll:
    def test_list_all_empty(self, subscription_repository) -> None:
        assert subscription_repository.list_all() == []

    def test_list_all_with_data(self, subscription_repository, db_session) -> None:
        plan = _insert_plan(db_session)
        subscription_repository.create(_build_subscription(plan.id, external_user_id="user_a"))
        subscription_repository.create(_build_subscription(plan.id, external_user_id="user_b"))
        assert len(subscription_repository.list_all()) == 2


class TestSubscriptionRepositoryUpdate:
    def test_update_status(self, subscription_repository, db_session) -> None:
        plan = _insert_plan(db_session)
        sub = subscription_repository.create(_build_subscription(plan.id))
        sub.status = "active"
        updated = subscription_repository.update(sub)
        assert updated.status == "active"


class TestSubscriptionRepositoryDelete:
    def test_delete_subscription(self, subscription_repository, db_session) -> None:
        plan = _insert_plan(db_session)
        sub = subscription_repository.create(_build_subscription(plan.id))
        subscription_repository.delete(sub)
        assert subscription_repository.get_by_id(sub.id) is None


class TestSubscriptionRepositoryFKConstraints:
    def test_create_with_invalid_plan_id_raises_integrity_error(self, subscription_repository, db_session) -> None:
        from sqlalchemy.exc import IntegrityError

        sub = _build_subscription(plan_id=99999)  # Non-existent plan_id
        with pytest.raises(IntegrityError):
            subscription_repository.create(sub)


class TestSubscriptionRepositoryGetExpiringSubscriptions:
    """测试获取即将到期的订阅。"""

    def test_returns_active_subscriptions_expiring_within_days(self, subscription_repository, db_session) -> None:
        """返回即将在指定天数内到期的 active 订阅。"""
        plan = _insert_plan(db_session)
        now = datetime.now(tz=UTC)

        # 即将到期（2天后）
        expiring_sub = subscription_repository.create(
            _build_subscription(
                plan.id,
                external_user_id="user_expiring",
                status="active",
                current_period_start=now,
                current_period_end=now + timedelta(days=2),
            )
        )
        # 还有很久才到期（30天后）
        active_sub = subscription_repository.create(
            _build_subscription(
                plan.id,
                external_user_id="user_active",
                status="active",
                current_period_start=now,
                current_period_end=now + timedelta(days=30),
            )
        )
        # 已过期（past_due 状态）
        past_due_sub = subscription_repository.create(
            _build_subscription(
                plan.id,
                external_user_id="user_past_due",
                status="past_due",
                current_period_start=now - timedelta(days=35),
                current_period_end=now - timedelta(days=5),
            )
        )

        result = subscription_repository.get_expiring_subscriptions(days=7)

        assert len(result) == 1
        assert result[0].id == expiring_sub.id
        assert result[0].status == "active"

    def test_returns_empty_when_no_subscriptions_expiring(self, subscription_repository, db_session) -> None:
        """没有即将到期的订阅时返回空列表。"""
        plan = _insert_plan(db_session)
        now = datetime.now(tz=UTC)

        subscription_repository.create(
            _build_subscription(
                plan.id,
                external_user_id="user_long",
                status="active",
                current_period_start=now,
                current_period_end=now + timedelta(days=30),
            )
        )

        result = subscription_repository.get_expiring_subscriptions(days=7)
        assert result == []

    def test_filters_by_active_status_only(self, subscription_repository, db_session) -> None:
        """仅返回 active 状态的订阅。"""
        plan = _insert_plan(db_session)
        now = datetime.now(tz=UTC)

        # trial 状态，即将到期
        subscription_repository.create(
            _build_subscription(
                plan.id,
                external_user_id="user_trial",
                status="trial",
                current_period_start=now,
                current_period_end=now + timedelta(days=2),
            )
        )
        # expired 状态
        subscription_repository.create(
            _build_subscription(
                plan.id,
                external_user_id="user_expired",
                status="expired",
                current_period_start=now - timedelta(days=40),
                current_period_end=now - timedelta(days=10),
            )
        )
        # active 状态，即将到期
        active_sub = subscription_repository.create(
            _build_subscription(
                plan.id,
                external_user_id="user_active",
                status="active",
                current_period_start=now,
                current_period_end=now + timedelta(days=2),
            )
        )

        result = subscription_repository.get_expiring_subscriptions(days=7)

        assert len(result) == 1
        assert result[0].id == active_sub.id

    def test_orders_by_current_period_end(self, subscription_repository, db_session) -> None:
        """结果按 current_period_end 升序排列。"""
        plan = _insert_plan(db_session)
        now = datetime.now(tz=UTC)

        sub1 = subscription_repository.create(
            _build_subscription(
                plan.id,
                external_user_id="user_1",
                status="active",
                current_period_start=now,
                current_period_end=now + timedelta(days=5),
            )
        )
        sub2 = subscription_repository.create(
            _build_subscription(
                plan.id,
                external_user_id="user_2",
                status="active",
                current_period_start=now,
                current_period_end=now + timedelta(days=1),
            )
        )
        sub3 = subscription_repository.create(
            _build_subscription(
                plan.id,
                external_user_id="user_3",
                status="active",
                current_period_start=now,
                current_period_end=now + timedelta(days=3),
            )
        )

        result = subscription_repository.get_expiring_subscriptions(days=7)

        assert len(result) == 3
        assert result[0].id == sub2.id  # 1天后到期
        assert result[1].id == sub3.id  # 3天后到期
        assert result[2].id == sub1.id  # 5天后到期

    def test_excludes_canceled_subscriptions(self, subscription_repository, db_session) -> None:
        """排除已取消的订阅。"""
        plan = _insert_plan(db_session)
        now = datetime.now(tz=UTC)

        # active 且即将到期
        active_sub = subscription_repository.create(
            _build_subscription(
                plan.id,
                external_user_id="user_active",
                status="active",
                current_period_start=now,
                current_period_end=now + timedelta(days=2),
            )
        )
        # canceled 且即将到期
        subscription_repository.create(
            _build_subscription(
                plan.id,
                external_user_id="user_canceled",
                status="active",
                current_period_start=now,
                current_period_end=now + timedelta(days=2),
                canceled_at=now,
            )
        )

        result = subscription_repository.get_expiring_subscriptions(days=7)

        assert len(result) == 1
        assert result[0].id == active_sub.id
