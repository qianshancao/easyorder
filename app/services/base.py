import logging

from app.models.base import Base
from app.repositories.base import BaseRepository


class BaseService[ModelType: Base]:
    def __init__(self, repo: BaseRepository[ModelType], domain_name: str) -> None:
        self.repo = repo
        self.domain_name = domain_name
        self.logger = logging.getLogger("app.services." + domain_name)

    def get(self, entity_id: int) -> ModelType | None:
        entity = self.repo.get_by_id(entity_id)
        if entity is None:
            self.logger.warning(
                self.domain_name + ".not_found",
                extra={self.domain_name + "_id": entity_id},
            )
        return entity

    def list_all(self) -> list[ModelType]:
        entities = self.repo.list_all()
        self.logger.info(
            self.domain_name + ".listed",
            extra={"count": len(entities)},
        )
        return entities
