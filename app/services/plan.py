import logging

from app.models.plan import Plan
from app.repositories.plan import PlanRepository
from app.schemas.plan import PlanCreate

logger = logging.getLogger(__name__)


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
        created = self.repo.create(plan)
        logger.info(
            "plan.created",
            extra={"plan_id": created.id, "name": created.name, "cycle": created.cycle},
        )
        return created

    def get_plan(self, plan_id: int) -> Plan | None:
        plan = self.repo.get_by_id(plan_id)
        if plan is None:
            logger.warning("plan.not_found", extra={"plan_id": plan_id})
        return plan

    def list_plans(self) -> list[Plan]:
        plans = self.repo.list_all()
        logger.info("plan.listed", extra={"count": len(plans)})
        return plans
