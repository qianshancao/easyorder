from collections.abc import Generator

from fastapi import Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.repositories.plan import PlanRepository
from app.services.plan import PlanService


def get_plan_service(db: Session = Depends(get_db)) -> Generator[PlanService, None, None]:
    repo = PlanRepository(db)
    yield PlanService(repo=repo)
