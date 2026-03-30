import logging

import bcrypt

from app.models.admin import Admin
from app.repositories.admin import AdminRepository
from app.schemas.admin import AdminCreate, AdminUpdate, PasswordChange
from app.services.base import BaseService

logger = logging.getLogger(__name__)


def _hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()


def _verify_password(password: str, hashed: str) -> bool:
    return bcrypt.checkpw(password.encode(), hashed.encode())


class AdminService(BaseService[Admin]):
    repo: AdminRepository  # type: ignore[assignment]

    def __init__(self, repo: AdminRepository) -> None:
        super().__init__(repo, domain_name="admin")

    def create_admin(self, data: AdminCreate) -> Admin:
        admin = Admin(
            username=data.username,
            password_hash=_hash_password(data.password),
            display_name=data.display_name,
            role=data.role,
        )
        created = self.repo.create(admin)
        logger.info(
            "admin.created",
            extra={"admin_id": created.id, "username": created.username, "role": created.role},
        )
        return created

    def update_admin(self, admin_id: int, data: AdminUpdate) -> Admin | None:
        admin = self.repo.get_by_id(admin_id)
        if admin is None:
            return None
        for field, value in data.model_dump(exclude_unset=True).items():
            setattr(admin, field, value)
        updated = self.repo.update(admin)
        logger.info(
            "admin.updated",
            extra={"admin_id": updated.id, "fields": list(data.model_dump(exclude_unset=True).keys())},
        )
        return updated

    def change_password(self, admin_id: int, data: PasswordChange) -> bool:
        admin = self.repo.get_by_id(admin_id)
        if admin is None:
            return False
        if not _verify_password(data.old_password, admin.password_hash):
            return False
        admin.password_hash = _hash_password(data.new_password)
        self.repo.update(admin)
        logger.info("admin.password_changed", extra={"admin_id": admin_id})
        return True

    def authenticate(self, username: str, password: str) -> Admin | None:
        admin = self.repo.get_by_username(username)
        if admin is None:
            return None
        if not _verify_password(password, admin.password_hash):
            return None
        if admin.status != "active":
            return None
        return admin

    def ensure_super_admin(self, username: str, password: str) -> Admin:
        existing = self.repo.get_by_username(username)
        if existing is not None:
            return existing
        admin = Admin(
            username=username,
            password_hash=_hash_password(password),
            role="super_admin",
        )
        created = self.repo.create(admin)
        logger.info(
            "admin.super_admin_created",
            extra={"admin_id": created.id, "username": created.username},
        )
        return created
