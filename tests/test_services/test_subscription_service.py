"""Tests for SubscriptionService."""

from datetime import UTC, datetime, timedelta
from unittest.mock import MagicMock

import pytest

from app.models.plan import Plan
from app.schemas.subscription import SubscriptionCreate
from app.services.subscription import CYCLE_DURATION_DAYS, SubscriptionService

from .conftest import _make_subscription_mock


def _make_plan_mock(**overrides) -> MagicMock:
    defaults = {
        "id": 1,
        "name": "Basic Plan",
        "cycle": "monthly",
        "base_price": 3000,
        "introductory_price": None,
        "trial_price": None,
        "trial_duration": None,
        "features": {"projects": 20},
        "status": "active",
    }
    defaults.update(overrides)
    mock = MagicMock(spec=Plan)
    for k, v in defaults.items():
        setattr(mock, k, v)
    return mock


class TestCreateSubscription:
    def test_with_trial(self, mock_subscription_repository, mock_plan_repository) -> None:
        plan = _make_plan_mock(trial_duration=7)
        mock_plan_repository.get_by_id.return_value = plan
        mock_subscription_repository.create.side_effect = lambda e: e
        service = SubscriptionService(mock_subscription_repository, mock_plan_repository)

        result = service.create_subscription(SubscriptionCreate(external_user_id="user_001", plan_id=1))

        assert result.status == "trial"
        assert result.external_user_id == "user_001"
        assert result.plan_id == 1
        assert result.plan_snapshot["name"] == "Basic Plan"
        assert result.plan_snapshot["features"] == {"projects": 20}

    def test_without_trial(self, mock_subscription_repository, mock_plan_repository) -> None:
        plan = _make_plan_mock()
        mock_plan_repository.get_by_id.return_value = plan
        mock_subscription_repository.create.side_effect = lambda e: e
        service = SubscriptionService(mock_subscription_repository, mock_plan_repository)

        result = service.create_subscription(SubscriptionCreate(external_user_id="user_001", plan_id=1))

        assert result.status == "active"
        expected_end = datetime.now(tz=UTC) + timedelta(days=CYCLE_DURATION_DAYS["monthly"])
        assert abs((result.current_period_end - expected_end).total_seconds()) < 5

    def test_plan_not_found_raises(self, mock_subscription_repository, mock_plan_repository) -> None:
        mock_plan_repository.get_by_id.return_value = None
        service = SubscriptionService(mock_subscription_repository, mock_plan_repository)

        with pytest.raises(ValueError, match="not found"):
            service.create_subscription(SubscriptionCreate(external_user_id="user_001", plan_id=999))

    def test_snapshot_includes_all_pricing_fields(self, mock_subscription_repository, mock_plan_repository) -> None:
        plan = _make_plan_mock(introductory_price=1000, trial_price=0, trial_duration=7, features={"storage": "10GB"})
        mock_plan_repository.get_by_id.return_value = plan
        mock_subscription_repository.create.side_effect = lambda e: e
        service = SubscriptionService(mock_subscription_repository, mock_plan_repository)

        result = service.create_subscription(SubscriptionCreate(external_user_id="user_001", plan_id=1))

        snap = result.plan_snapshot
        assert snap["base_price"] == 3000
        assert snap["introductory_price"] == 1000
        assert snap["trial_price"] == 0
        assert snap["trial_duration"] == 7
        assert snap["features"] == {"storage": "10GB"}

    def test_quarterly_cycle_period(self, mock_subscription_repository, mock_plan_repository) -> None:
        plan = _make_plan_mock(cycle="quarterly")
        mock_plan_repository.get_by_id.return_value = plan
        mock_subscription_repository.create.side_effect = lambda e: e
        service = SubscriptionService(mock_subscription_repository, mock_plan_repository)

        result = service.create_subscription(SubscriptionCreate(external_user_id="user_001", plan_id=1))

        expected_end = result.current_period_start + timedelta(days=90)
        assert result.current_period_end == expected_end

    def test_yearly_cycle_period(self, mock_subscription_repository, mock_plan_repository) -> None:
        plan = _make_plan_mock(cycle="yearly")
        mock_plan_repository.get_by_id.return_value = plan
        mock_subscription_repository.create.side_effect = lambda e: e
        service = SubscriptionService(mock_subscription_repository, mock_plan_repository)

        result = service.create_subscription(SubscriptionCreate(external_user_id="user_001", plan_id=1))

        expected_end = result.current_period_start + timedelta(days=365)
        assert result.current_period_end == expected_end


class TestGetSubscription:
    def test_found(self, mock_subscription_repository, mock_plan_repository) -> None:
        sub = _make_subscription_mock()
        mock_subscription_repository.get_by_id.return_value = sub
        service = SubscriptionService(mock_subscription_repository, mock_plan_repository)

        result = service.get_subscription(1)
        assert result is sub

    def test_not_found(self, mock_subscription_repository, mock_plan_repository) -> None:
        mock_subscription_repository.get_by_id.return_value = None
        service = SubscriptionService(mock_subscription_repository, mock_plan_repository)

        result = service.get_subscription(999)
        assert result is None


class TestListByExternalUserId:
    def test_returns_results(self, mock_subscription_repository, mock_plan_repository) -> None:
        subs = [_make_subscription_mock(), _make_subscription_mock(id=2)]
        mock_subscription_repository.get_by_external_user_id.return_value = subs
        service = SubscriptionService(mock_subscription_repository, mock_plan_repository)

        result = service.list_by_external_user_id("user_001")
        assert len(result) == 2

    def test_empty(self, mock_subscription_repository, mock_plan_repository) -> None:
        mock_subscription_repository.get_by_external_user_id.return_value = []
        service = SubscriptionService(mock_subscription_repository, mock_plan_repository)

        result = service.list_by_external_user_id("nobody")
        assert result == []


class TestCancelSubscription:
    def test_success_from_active(self, mock_subscription_repository, mock_plan_repository) -> None:
        sub = _make_subscription_mock(status="active")
        mock_subscription_repository.get_by_id.return_value = sub
        mock_subscription_repository.update.side_effect = lambda e: e
        service = SubscriptionService(mock_subscription_repository, mock_plan_repository)

        result = service.cancel_subscription(1)
        assert result.status == "canceled"
        assert result.canceled_at is not None

    def test_success_from_past_due(self, mock_subscription_repository, mock_plan_repository) -> None:
        sub = _make_subscription_mock(status="past_due")
        mock_subscription_repository.get_by_id.return_value = sub
        mock_subscription_repository.update.side_effect = lambda e: e
        service = SubscriptionService(mock_subscription_repository, mock_plan_repository)

        result = service.cancel_subscription(1)
        assert result.status == "canceled"

    def test_not_found(self, mock_subscription_repository, mock_plan_repository) -> None:
        mock_subscription_repository.get_by_id.return_value = None
        service = SubscriptionService(mock_subscription_repository, mock_plan_repository)

        result = service.cancel_subscription(999)
        assert result is None

    def test_invalid_from_trial(self, mock_subscription_repository, mock_plan_repository) -> None:
        sub = _make_subscription_mock(status="trial")
        mock_subscription_repository.get_by_id.return_value = sub
        service = SubscriptionService(mock_subscription_repository, mock_plan_repository)

        with pytest.raises(ValueError, match="Invalid status transition"):
            service.cancel_subscription(1)

    def test_invalid_from_canceled(self, mock_subscription_repository, mock_plan_repository) -> None:
        sub = _make_subscription_mock(status="canceled")
        mock_subscription_repository.get_by_id.return_value = sub
        service = SubscriptionService(mock_subscription_repository, mock_plan_repository)

        with pytest.raises(ValueError, match="Invalid status transition"):
            service.cancel_subscription(1)

    def test_invalid_from_expired(self, mock_subscription_repository, mock_plan_repository) -> None:
        sub = _make_subscription_mock(status="expired")
        mock_subscription_repository.get_by_id.return_value = sub
        service = SubscriptionService(mock_subscription_repository, mock_plan_repository)

        with pytest.raises(ValueError, match="Invalid status transition"):
            service.cancel_subscription(1)


class TestReactivateSubscription:
    def test_from_past_due(self, mock_subscription_repository, mock_plan_repository) -> None:
        sub = _make_subscription_mock(status="past_due")
        mock_subscription_repository.get_by_id.return_value = sub
        mock_subscription_repository.update.side_effect = lambda e: e
        service = SubscriptionService(mock_subscription_repository, mock_plan_repository)

        result = service.reactivate_subscription(1)
        assert result.status == "active"
        assert result.canceled_at is None
        assert result.current_period_start is not None
        assert result.current_period_end is not None
        assert result.current_period_end == result.current_period_start + timedelta(days=CYCLE_DURATION_DAYS["monthly"])

    def test_not_found(self, mock_subscription_repository, mock_plan_repository) -> None:
        mock_subscription_repository.get_by_id.return_value = None
        service = SubscriptionService(mock_subscription_repository, mock_plan_repository)

        result = service.reactivate_subscription(999)
        assert result is None

    def test_invalid_from_active(self, mock_subscription_repository, mock_plan_repository) -> None:
        sub = _make_subscription_mock(status="active")
        mock_subscription_repository.get_by_id.return_value = sub
        service = SubscriptionService(mock_subscription_repository, mock_plan_repository)

        with pytest.raises(ValueError, match="Invalid status transition"):
            service.reactivate_subscription(1)

    def test_invalid_from_canceled(self, mock_subscription_repository, mock_plan_repository) -> None:
        sub = _make_subscription_mock(status="canceled")
        mock_subscription_repository.get_by_id.return_value = sub
        service = SubscriptionService(mock_subscription_repository, mock_plan_repository)

        with pytest.raises(ValueError, match="Invalid status transition"):
            service.reactivate_subscription(1)

    def test_from_trial_to_active(self, mock_subscription_repository, mock_plan_repository) -> None:
        sub = _make_subscription_mock(status="trial")
        mock_subscription_repository.get_by_id.return_value = sub
        mock_subscription_repository.update.side_effect = lambda e: e
        service = SubscriptionService(mock_subscription_repository, mock_plan_repository)

        result = service.reactivate_subscription(1)
        assert result.status == "active"
        assert result.canceled_at is None

    def test_invalid_from_expired(self, mock_subscription_repository, mock_plan_repository) -> None:
        sub = _make_subscription_mock(status="expired")
        mock_subscription_repository.get_by_id.return_value = sub
        service = SubscriptionService(mock_subscription_repository, mock_plan_repository)

        with pytest.raises(ValueError, match="Invalid status transition"):
            service.reactivate_subscription(1)
