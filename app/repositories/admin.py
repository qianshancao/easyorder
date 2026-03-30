from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.admin import Admin
from app.repositories.base import BaseRepository


class AdminRepository(BaseRepository[Admin]):
    def __init__(self, db: Session) -> None:
        super().__init__(Admin, db)

    def get_by_username(self, username: str) -> Admin | None:
        stmt = select(Admin).where(Admin.username == username)
        return self.db.execute(stmt).scalar_one_or_none()
