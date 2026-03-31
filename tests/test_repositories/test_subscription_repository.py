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
