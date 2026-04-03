"""Tests for PlanService with a mocked PlanRepository."""

from unittest.mock import MagicMock

import pytest

from app.models.plan import Plan
from app.schemas.plan import PlanCreate, PlanUpdate
from app.services.plan import PlanService


def _build_plan_create(**overrides: object) -> PlanCreate:
    """Helper to create a PlanCreate schema with sensible defaults."""
    defaults: dict[str, object] = {
        "name": "Basic Plan",
        "cycle": "monthly",
        "base_price": 3000,
    }
    defaults.update(overrides)
    return PlanCreate(**defaults)  # type: ignore[arg-type]


def _build_plan_orm(**overrides: object) -> Plan:
    """Helper to create a Plan ORM instance with sensible defaults."""
    defaults: dict[str, object] = {
        "id": 1,
        "name": "Basic Plan",
        "cycle": "monthly",
        "base_price": 3000,
        "status": "active",
    }
    defaults.update(overrides)
    return Plan(**defaults)  # type: ignore[arg-type]


class TestPlanServiceCreatePlan:
    """Tests for PlanService.create_plan."""

    def test_create_plan_delegates_to_repo(self, mock_plan_repository: MagicMock) -> None:
        service = PlanService(repo=mock_plan_repository)
        expected_plan = _build_plan_orm()
        mock_plan_repository.create.return_value = expected_plan

        result = service.create_plan(_build_plan_create())

        mock_plan_repository.create.assert_called_once()
        assert result == expected_plan

    def test_create_plan_passes_correct_fields(self, mock_plan_repository: MagicMock) -> None:
        service = PlanService(repo=mock_plan_repository)
        mock_plan_repository.create.return_value = _build_plan_orm(name="Pro")

        service.create_plan(_build_plan_create(name="Pro", cycle="yearly", base_price=5000, introductory_price=1000))

        call_args = mock_plan_repository.create.call_args
        created_plan = call_args[0][0]
        assert created_plan.name == "Pro"
        assert created_plan.cycle == "yearly"
        assert created_plan.base_price == 5000
        assert created_plan.introductory_price == 1000


class TestPlanServiceGetPlan:
    """Tests for PlanService.get_plan."""

    def test_get_plan_found(self, mock_plan_repository: MagicMock) -> None:
        service = PlanService(repo=mock_plan_repository)
        expected = _build_plan_orm()
        mock_plan_repository.get_by_id.return_value = expected

        result = service.get_plan(1)

        mock_plan_repository.get_by_id.assert_called_once_with(1)
        assert result == expected

    def test_get_plan_not_found(self, mock_plan_repository: MagicMock) -> None:
        service = PlanService(repo=mock_plan_repository)
        mock_plan_repository.get_by_id.return_value = None

        result = service.get_plan(999)

        assert result is None


class TestPlanServiceListPlans:
    """Tests for PlanService.list_plans."""

    def test_list_plans_returns_all(self, mock_plan_repository: MagicMock) -> None:
        service = PlanService(repo=mock_plan_repository)
        expected = [_build_plan_orm(id=1), _build_plan_orm(id=2, name="Pro")]
        mock_plan_repository.list_all.return_value = expected

        result = service.list_plans()

        mock_plan_repository.list_all.assert_called_once()
        assert result == expected
        assert len(result) == 2


class TestPlanServiceUpdatePlan:
    """Tests for PlanService.update_plan."""

    def test_update_plan_success(self, mock_plan_repository: MagicMock) -> None:
        service = PlanService(repo=mock_plan_repository)
        existing = _build_plan_orm()
        mock_plan_repository.get_by_id.return_value = existing
        mock_plan_repository.update.return_value = existing

        result = service.update_plan(1, PlanUpdate(name="Pro Plan", base_price=5000))

        assert result == existing
        mock_plan_repository.get_by_id.assert_called_once_with(1)
        mock_plan_repository.update.assert_called_once_with(existing)

    def test_update_plan_not_found(self, mock_plan_repository: MagicMock) -> None:
        service = PlanService(repo=mock_plan_repository)
        mock_plan_repository.get_by_id.return_value = None

        result = service.update_plan(999, PlanUpdate(name="New Name"))

        assert result is None
        mock_plan_repository.update.assert_not_called()

    def test_update_plan_partial_fields(self, mock_plan_repository: MagicMock) -> None:
        service = PlanService(repo=mock_plan_repository)
        existing = _build_plan_orm(base_price=3000)
        mock_plan_repository.get_by_id.return_value = existing
        mock_plan_repository.update.return_value = existing

        service.update_plan(1, PlanUpdate(base_price=5000))

        assert existing.base_price == 5000
        # name should NOT be changed since it was not in the update
        assert existing.name == "Basic Plan"


class TestPlanServiceDeletePlan:
    """Tests for PlanService.delete_plan."""

    def test_delete_plan_success(self, mock_plan_repository: MagicMock) -> None:
        mock_subscription_repo = MagicMock()
        mock_subscription_repo.count_by_plan_id.return_value = 0
        service = PlanService(repo=mock_plan_repository, subscription_repo=mock_subscription_repo)

        existing = _build_plan_orm()
        mock_plan_repository.get_by_id.return_value = existing

        result = service.delete_plan(1)

        assert result is True
        mock_plan_repository.delete.assert_called_once_with(existing)

    def test_delete_plan_not_found(self, mock_plan_repository: MagicMock) -> None:
        mock_subscription_repo = MagicMock()
        service = PlanService(repo=mock_plan_repository, subscription_repo=mock_subscription_repo)
        mock_plan_repository.get_by_id.return_value = None

        result = service.delete_plan(999)

        assert result is False
        mock_plan_repository.delete.assert_not_called()

    def test_delete_plan_with_subscriptions_raises(self, mock_plan_repository: MagicMock) -> None:
        mock_subscription_repo = MagicMock()
        mock_subscription_repo.count_by_plan_id.return_value = 3
        service = PlanService(repo=mock_plan_repository, subscription_repo=mock_subscription_repo)

        mock_plan_repository.get_by_id.return_value = _build_plan_orm()

        with pytest.raises(ValueError, match="无法删除"):
            service.delete_plan(1)
        mock_plan_repository.delete.assert_not_called()


class TestPlanServiceTogglePlanStatus:
    """Tests for PlanService.toggle_plan_status."""

    def test_activate_plan(self, mock_plan_repository: MagicMock) -> None:
        service = PlanService(repo=mock_plan_repository)
        plan = _build_plan_orm(status="inactive")
        mock_plan_repository.get_by_id.return_value = plan
        mock_plan_repository.update.return_value = plan

        result = service.toggle_plan_status(1, "active")

        assert result == plan
        assert plan.status == "active"
        mock_plan_repository.update.assert_called_once_with(plan)

    def test_deactivate_plan(self, mock_plan_repository: MagicMock) -> None:
        service = PlanService(repo=mock_plan_repository)
        plan = _build_plan_orm(status="active")
        mock_plan_repository.get_by_id.return_value = plan
        mock_plan_repository.update.return_value = plan

        result = service.toggle_plan_status(1, "inactive")

        assert result == plan
        assert plan.status == "inactive"

    def test_toggle_plan_not_found(self, mock_plan_repository: MagicMock) -> None:
        service = PlanService(repo=mock_plan_repository)
        mock_plan_repository.get_by_id.return_value = None

        result = service.toggle_plan_status(999, "active")

        assert result is None
