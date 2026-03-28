"""Tests for PlanService with a mocked PlanRepository."""

from unittest.mock import MagicMock

from app.models.plan import Plan
from app.schemas.plan import PlanCreate
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
