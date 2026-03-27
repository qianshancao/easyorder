from app.models.plan import Plan
from app.repositories.plan import PlanRepository
from app.schemas.plan import PlanCreate


class PlanService:
    def __init__(self, repo: PlanRepository) -> None:
        self.repo = repo

    def create_plan(self, data: PlanCreate) -> Plan:
        plan = Plan(
            name=data.name,
            cycle=data.cycle,
            base_price=data.base_price,
            introductory_price=data.introductory_price,
            trial_price=data.trial_price,
            trial_duration=data.trial_duration,
            features=data.features,
            renewal_rules=data.renewal_rules,
        )
        return self.repo.create(plan)

    def get_plan(self, plan_id: int) -> Plan | None:
        return self.repo.get_by_id(plan_id)

    def list_plans(self) -> list[Plan]:
        return self.repo.list_all()
