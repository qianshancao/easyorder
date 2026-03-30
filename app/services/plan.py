import logging

from app.models.plan import Plan
from app.repositories.plan import PlanRepository
from app.schemas.plan import PlanCreate
from app.services.base import BaseService

logger = logging.getLogger(__name__)


class PlanService(BaseService[Plan]):
    def __init__(self, repo: PlanRepository) -> None:
        super().__init__(repo, domain_name="plan")

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
        created = self.repo.create(plan)
        logger.info(
            "plan.created",
            extra={"plan_id": created.id, "plan_name": created.name, "cycle": created.cycle},
        )
        return created

    def get_plan(self, plan_id: int) -> Plan | None:
        return self.get(plan_id)

    def list_plans(self) -> list[Plan]:
        return self.list_all()
