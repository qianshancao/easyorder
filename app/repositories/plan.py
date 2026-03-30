from sqlalchemy.orm import Session

from app.models.plan import Plan
from app.repositories.base import BaseRepository


class PlanRepository(BaseRepository[Plan]):
    def __init__(self, db: Session) -> None:
        super().__init__(Plan, db)
