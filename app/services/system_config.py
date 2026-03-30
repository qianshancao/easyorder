import logging

from app.models.system_config import SystemConfig
from app.repositories.system_config import SystemConfigRepository
from app.schemas.system_config import SystemConfigCreate, SystemConfigUpdate
from app.services.base import BaseService

logger = logging.getLogger(__name__)


class SystemConfigService(BaseService[SystemConfig]):
    repo: SystemConfigRepository  # type: ignore[assignment]

    def __init__(self, repo: SystemConfigRepository) -> None:
        super().__init__(repo, domain_name="system_config")

    def create_config(self, data: SystemConfigCreate) -> SystemConfig:
        config = SystemConfig(
            key=data.key,
            value=data.value,
            description=data.description,
        )
        created = self.repo.create(config)
        logger.info("system_config.created", extra={"config_key": created.key})
        return created

    def update_config(self, config_id: int, data: SystemConfigUpdate) -> SystemConfig | None:
        config = self.repo.get_by_id(config_id)
        if config is None:
            return None
        for field, value in data.model_dump(exclude_unset=True).items():
            setattr(config, field, value)
        updated = self.repo.update(config)
        logger.info("system_config.updated", extra={"config_key": updated.key})
        return updated

    def get_value(self, key: str) -> dict[str, object] | None:
        config = self.repo.get_by_key(key)
        if config is None:
            return None
        return config.value
