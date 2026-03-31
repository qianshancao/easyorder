"""Tests for AdminRepository."""

import pytest
from sqlalchemy.exc import IntegrityError

from app.models.admin import Admin


class TestAdminRepositoryCreate:
    def test_create_admin_success(self, admin_repository) -> None:
        admin = Admin(username="alice", password_hash="hashed", role="admin")
        created = admin_repository.create(admin)
        assert created.id is not None
        assert created.username == "alice"
        assert created.role == "admin"
        assert created.status == "active"
        assert created.created_at is not None

    def test_create_admin_with_optional_fields(self, admin_repository) -> None:
        admin = Admin(username="bob", password_hash="hashed", display_name="Bob", role="super_admin")
        created = admin_repository.create(admin)
        assert created.display_name == "Bob"


class TestAdminRepositoryGetById:
    def test_get_by_id_found(self, admin_repository) -> None:
        admin = admin_repository.create(Admin(username="alice", password_hash="h"))
        result = admin_repository.get_by_id(admin.id)
        assert result is not None
        assert result.username == "alice"

    def test_get_by_id_not_found(self, admin_repository) -> None:
        assert admin_repository.get_by_id(999) is None


class TestAdminRepositoryGetByUsername:
    def test_get_by_username_found(self, admin_repository) -> None:
        admin_repository.create(Admin(username="alice", password_hash="h"))
        result = admin_repository.get_by_username("alice")
        assert result is not None
        assert result.username == "alice"

    def test_get_by_username_not_found(self, admin_repository) -> None:
        assert admin_repository.get_by_username("nonexistent") is None


class TestAdminRepositoryListAll:
    def test_list_all_empty(self, admin_repository) -> None:
        assert admin_repository.list_all() == []

    def test_list_all_with_data(self, admin_repository) -> None:
        admin_repository.create(Admin(username="alice", password_hash="h1"))
        admin_repository.create(Admin(username="bob", password_hash="h2"))
        result = admin_repository.list_all()
        assert len(result) == 2


class TestAdminRepositoryUniqueConstraints:
    def test_create_duplicate_username_raises_integrity_error(self, admin_repository) -> None:
        admin_repository.create(Admin(username="alice", password_hash="h1"))
        with pytest.raises(IntegrityError):
            admin_repository.create(Admin(username="alice", password_hash="h2"))


class TestAdminRepositoryUpdate:
    def test_update_display_name(self, admin_repository) -> None:
        admin = admin_repository.create(Admin(username="alice", password_hash="hash123"))
        admin.display_name = "Alice Updated"
        updated = admin_repository.update(admin)
        assert updated.display_name == "Alice Updated"


class TestAdminRepositoryDelete:
    def test_delete_admin(self, admin_repository) -> None:
        admin = admin_repository.create(Admin(username="alice", password_hash="hash123"))
        admin_repository.delete(admin)
        assert admin_repository.get_by_id(admin.id) is None
