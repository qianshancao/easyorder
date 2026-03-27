from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.plan import Plan


class PlanRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def create(self, plan: Plan) -> Plan:
        self.db.add(plan)
        self.db.commit()
        self.db.refresh(plan)
        return plan

    def get_by_id(self, plan_id: int) -> Plan | None:
        stmt = select(Plan).where(Plan.id == plan_id)
        return self.db.execute(stmt).scalar_one_or_none()

    def list_all(self) -> list[Plan]:
        stmt = select(Plan).order_by(Plan.id)
        return list(self.db.execute(stmt).scalars().all())
