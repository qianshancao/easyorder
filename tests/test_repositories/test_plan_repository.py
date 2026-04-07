"""Tests for PlanRepository against a real in-memory SQLite database."""

from app.models.plan import Plan
from app.repositories.plan import PlanRepository


def _build_plan(**overrides: object) -> Plan:
    """Helper to create a Plan ORM instance with sensible defaults."""
    defaults: dict[str, object] = {
        "name": "Basic Plan",
        "cycle": "monthly",
        "base_price": 3000,
    }
    defaults.update(overrides)
    return Plan(**defaults)  # type: ignore[arg-type]


class TestPlanRepositoryCreate:
    """Tests for PlanRepository.create."""

    def test_create_plan_success(self, plan_repository: PlanRepository) -> None:
        plan = _build_plan()
        result = plan_repository.create(plan)

        assert result.id is not None
        assert result.name == "Basic Plan"
        assert result.cycle == "monthly"
        assert result.base_price == 3000
        assert result.status == "active"
        assert result.created_at is not None

    def test_create_plan_with_optional_fields(self, plan_repository: PlanRepository) -> None:
        plan = _build_plan(
            introductory_price=1000,
            trial_price=0,
            trial_duration=7,
            features={"projects": 5},
            renewal_rules={"grace_period_days": 3},
        )
        result = plan_repository.create(plan)

        assert result.introductory_price == 1000
        assert result.trial_price == 0
        assert result.trial_duration == 7
        assert result.features == {"projects": 5}
        assert result.renewal_rules == {"grace_period_days": 3}


class TestPlanRepositoryGetById:
    """Tests for PlanRepository.get_by_id."""

    def test_get_by_id_found(self, plan_repository: PlanRepository) -> None:
        created = plan_repository.create(_build_plan())

        result = plan_repository.get_by_id(created.id)

        assert result is not None
        assert result.id == created.id
        assert result.name == "Basic Plan"

    def test_get_by_id_not_found(self, plan_repository: PlanRepository) -> None:
        result = plan_repository.get_by_id(99999)

        assert result is None


class TestPlanRepositoryListAll:
    """Tests for PlanRepository.list_all."""

    def test_list_all_empty(self, plan_repository: PlanRepository) -> None:
        result = plan_repository.list_all()

        assert result == []

    def test_list_all_with_data(self, plan_repository: PlanRepository) -> None:
        plan_repository.create(_build_plan(name="Plan A", base_price=1000))
        plan_repository.create(_build_plan(name="Plan B", base_price=2000))

        result = plan_repository.list_all()

        assert len(result) == 2
        assert result[0].name == "Plan B"
        assert result[1].name == "Plan A"

    def test_list_all_ordered_by_id(self, plan_repository: PlanRepository) -> None:
        p1 = plan_repository.create(_build_plan(name="Zeta"))
        p2 = plan_repository.create(_build_plan(name="Alpha"))

        result = plan_repository.list_all()

        assert result[0].id == p2.id
        assert result[1].id == p1.id


class TestPlanRepositoryUpdate:
    def test_update_name(self, plan_repository: PlanRepository) -> None:
        plan = plan_repository.create(_build_plan())
        plan.name = "Pro Plan"
        updated = plan_repository.update(plan)
        assert updated.name == "Pro Plan"


class TestPlanRepositoryDelete:
    def test_delete_plan(self, plan_repository: PlanRepository) -> None:
        plan = plan_repository.create(_build_plan())
        plan_repository.delete(plan)
        assert plan_repository.get_by_id(plan.id) is None
