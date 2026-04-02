"""Tests for AdminService."""

import bcrypt

from app.schemas.admin import AdminCreate, AdminUpdate, PasswordChange
from app.services.admin import AdminService

from .conftest import _make_admin_mock


class TestAdminServiceCreateAdmin:
    def test_create_admin_hashes_password(self, mock_admin_repository) -> None:
        mock_admin_repository.create.side_effect = lambda e: e
        service = AdminService(mock_admin_repository)
        data = AdminCreate(username="alice", password="secret123")
        admin = service.create_admin(data)
        assert admin.username == "alice"
        # Password should be hashed, not plaintext
        assert admin.password_hash != "secret123"
        assert bcrypt.checkpw(b"secret123", admin.password_hash.encode())

    def test_create_admin_sets_role(self, mock_admin_repository) -> None:
        mock_admin_repository.create.side_effect = lambda e: e
        service = AdminService(mock_admin_repository)
        data = AdminCreate(username="bob", password="pass", role="super_admin")
        admin = service.create_admin(data)
        assert admin.role == "super_admin"


class TestAdminServiceUpdateAdmin:
    def test_update_admin_success(self, mock_admin_repository) -> None:
        existing = _make_admin_mock(display_name="Old")
        mock_admin_repository.get_by_id.return_value = existing
        mock_admin_repository.update.side_effect = lambda e: e
        service = AdminService(mock_admin_repository)
        result = service.update_admin(1, AdminUpdate(display_name="New"))
        assert result is not None
        assert result.display_name == "New"
        mock_admin_repository.update.assert_called_once()

    def test_update_admin_not_found(self, mock_admin_repository) -> None:
        mock_admin_repository.get_by_id.return_value = None
        service = AdminService(mock_admin_repository)
        result = service.update_admin(999, AdminUpdate(display_name="New"))
        assert result is None

    def test_update_admin_partial_update(self, mock_admin_repository) -> None:
        existing = _make_admin_mock(display_name="Old", role="admin")
        mock_admin_repository.get_by_id.return_value = existing
        mock_admin_repository.update.side_effect = lambda e: e
        service = AdminService(mock_admin_repository)
        result = service.update_admin(1, AdminUpdate(display_name="New"))
        assert result is not None
        assert result.display_name == "New"
        assert result.role == "admin"  # unchanged
        mock_admin_repository.update.assert_called_once()


class TestAdminServiceChangePassword:
    def test_change_password_success(self, mock_admin_repository) -> None:
        admin = _make_admin_mock()
        mock_admin_repository.get_by_id.return_value = admin
        mock_admin_repository.update.side_effect = lambda e: e
        service = AdminService(mock_admin_repository)
        result = service.change_password(1, PasswordChange(old_password="password123", new_password="newpass"))
        assert result is True

    def test_change_password_wrong_old_password(self, mock_admin_repository) -> None:
        admin = _make_admin_mock()
        mock_admin_repository.get_by_id.return_value = admin
        service = AdminService(mock_admin_repository)
        result = service.change_password(1, PasswordChange(old_password="wrong", new_password="newpass"))
        assert result is False

    def test_change_password_admin_not_found(self, mock_admin_repository) -> None:
        mock_admin_repository.get_by_id.return_value = None
        service = AdminService(mock_admin_repository)
        result = service.change_password(999, PasswordChange(old_password="old", new_password="new"))
        assert result is False


class TestAdminServiceAuthenticate:
    def test_authenticate_success(self, mock_admin_repository) -> None:
        admin = _make_admin_mock()
        mock_admin_repository.get_by_username.return_value = admin
        service = AdminService(mock_admin_repository)
        result = service.authenticate("testadmin", "password123")
        assert result is not None
        assert result.username == "testadmin"

    def test_authenticate_wrong_password(self, mock_admin_repository) -> None:
        admin = _make_admin_mock()
        mock_admin_repository.get_by_username.return_value = admin
        service = AdminService(mock_admin_repository)
        result = service.authenticate("testadmin", "wrongpass")
        assert result is None

    def test_authenticate_user_not_found(self, mock_admin_repository) -> None:
        mock_admin_repository.get_by_username.return_value = None
        service = AdminService(mock_admin_repository)
        result = service.authenticate("nobody", "password123")
        assert result is None

    def test_authenticate_inactive_admin(self, mock_admin_repository) -> None:
        admin = _make_admin_mock(status="inactive")
        mock_admin_repository.get_by_username.return_value = admin
        service = AdminService(mock_admin_repository)
        result = service.authenticate("testadmin", "password123")
        assert result is None


class TestAdminServiceEnsureSuperAdmin:
    def test_creates_when_not_exists(self, mock_admin_repository) -> None:
        mock_admin_repository.get_by_username.return_value = None
        mock_admin_repository.create.side_effect = lambda e: e
        service = AdminService(mock_admin_repository)
        admin = service.ensure_super_admin("super", "pass123")
        assert admin.username == "super"
        assert admin.role == "super_admin"

    def test_returns_existing_when_exists(self, mock_admin_repository) -> None:
        existing = _make_admin_mock(role="super_admin")
        mock_admin_repository.get_by_username.return_value = existing
        service = AdminService(mock_admin_repository)
        admin = service.ensure_super_admin("super", "pass123")
        assert admin is existing
        mock_admin_repository.create.assert_not_called()
