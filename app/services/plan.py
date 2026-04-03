from app.models.plan import Plan
from app.repositories.plan import PlanRepository
from app.repositories.subscription import SubscriptionRepository
from app.schemas.plan import PlanCreate, PlanUpdate
from app.services.base import BaseService


class PlanService(BaseService[Plan]):
    def __init__(self, repo: PlanRepository, subscription_repo: SubscriptionRepository | None = None) -> None:
        super().__init__(repo, domain_name="plan")
        self.subscription_repo = subscription_repo

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
        self.logger.info(
            "plan.created",
            extra={"plan_id": created.id, "plan_name": created.name, "cycle": created.cycle},
        )
        return created

    def get_plan(self, plan_id: int) -> Plan | None:
        return self.get(plan_id)

    def list_plans(self) -> list[Plan]:
        return self.list_all()

    def update_plan(self, plan_id: int, data: PlanUpdate) -> Plan | None:
        plan = self.get(plan_id)
        if plan is None:
            return None
        changes = data.model_dump(exclude_unset=True)
        for field, value in changes.items():
            setattr(plan, field, value)
        updated = self.repo.update(plan)
        self.logger.info(
            "plan.updated",
            extra={"plan_id": updated.id, "fields": list(changes.keys())},
        )
        return updated

    def delete_plan(self, plan_id: int) -> bool:
        plan = self.get(plan_id)
        if plan is None:
            return False
        if self.subscription_repo is not None:
            count = self.subscription_repo.count_by_plan_id(plan_id)
            if count > 0:
                raise ValueError(f"套餐已有 {count} 个订阅, 无法删除")
        self.repo.delete(plan)
        self.logger.info("plan.deleted", extra={"plan_id": plan_id})
        return True

    def toggle_plan_status(self, plan_id: int, status: str) -> Plan | None:
        plan = self.get(plan_id)
        if plan is None:
            return None
        plan.status = status
        updated = self.repo.update(plan)
        self.logger.info("plan.status_changed", extra={"plan_id": updated.id, "status": status})
        return updated
