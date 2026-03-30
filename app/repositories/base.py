from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.base import Base


class BaseRepository[ModelType: Base]:
    def __init__(self, model: type[ModelType], db: Session) -> None:
        self.model = model
        self.db = db

    def create(self, entity: ModelType) -> ModelType:
        self.db.add(entity)
        self.db.commit()
        self.db.refresh(entity)
        return entity

    def get_by_id(self, entity_id: int) -> ModelType | None:
        stmt = select(self.model).where(self.model.id == entity_id)
        return self.db.execute(stmt).scalar_one_or_none()

    def list_all(self) -> list[ModelType]:
        stmt = select(self.model).order_by(self.model.id)
        return list(self.db.execute(stmt).scalars().all())

    def update(self, entity: ModelType) -> ModelType:
        self.db.commit()
        self.db.refresh(entity)
        return entity

    def delete(self, entity: ModelType) -> None:
        self.db.delete(entity)
        self.db.commit()
