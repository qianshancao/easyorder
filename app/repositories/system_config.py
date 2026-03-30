from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.system_config import SystemConfig
from app.repositories.base import BaseRepository


class SystemConfigRepository(BaseRepository[SystemConfig]):
    def __init__(self, db: Session) -> None:
        super().__init__(SystemConfig, db)

    def get_by_key(self, key: str) -> SystemConfig | None:
        stmt = select(SystemConfig).where(SystemConfig.key == key)
        return self.db.execute(stmt).scalar_one_or_none()
