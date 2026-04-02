"""Tests for AuthService."""

from datetime import UTC, datetime, timedelta
from unittest.mock import MagicMock

import jwt

from app.config import settings
from app.services.auth import AuthService

from .conftest import _make_admin_mock, _make_oauth_client_mock


def _make_service(
    mock_admin_repo: MagicMock | None = None,
    mock_oauth_repo: MagicMock | None = None,
) -> AuthService:
    return AuthService(mock_admin_repo or MagicMock(), mock_oauth_repo or MagicMock())


class TestAuthServiceCreateAdminToken:
    def test_returns_valid_jwt(self) -> None:
        service = _make_service()
        admin = _make_admin_mock()
        token = service.create_admin_token(admin)
        payload = jwt.decode(token, settings.secret_key, algorithms=["HS256"])
        assert payload["sub"] == "1"
        assert payload["role"] == "admin"
        assert payload["type"] == "admin"
        assert "exp" in payload

    def test_token_has_correct_expiry(self) -> None:
        service = _make_service()
        admin = _make_admin_mock()
        token = service.create_admin_token(admin)
        payload = jwt.decode(token, settings.secret_key, algorithms=["HS256"])
        assert payload["exp"] > datetime.now(tz=UTC).timestamp()


class TestAuthServiceCreateApiToken:
    def test_returns_token_and_expiry(self) -> None:
        service = _make_service()
        client = _make_oauth_client_mock()
        token, expires_in = service.create_api_token(client)
        assert isinstance(token, str)
        assert expires_in == settings.api_token_expire_seconds

    def test_payload_has_api_type(self) -> None:
        service = _make_service()
        client = _make_oauth_client_mock()
        token, _ = service.create_api_token(client)
        payload = jwt.decode(token, settings.secret_key, algorithms=["HS256"])
        assert payload["type"] == "api"
        assert payload["sub"] == "test_client_id"


class TestAuthServiceVerifyToken:
    def test_verify_valid_token(self) -> None:
        service = _make_service()
        admin = _make_admin_mock()
        token = service.create_admin_token(admin)
        payload = service.verify_token(token)
        assert payload is not None
        assert payload["type"] == "admin"

    def test_verify_expired_token(self) -> None:
        payload = {
            "sub": "1",
            "type": "admin",
            "exp": datetime.now(tz=UTC) - timedelta(hours=1),
        }
        token = jwt.encode(payload, settings.secret_key, algorithm="HS256")
        service = _make_service()
        assert service.verify_token(token) is None

    def test_verify_invalid_token(self) -> None:
        service = _make_service()
        assert service.verify_token("garbage.token.here") is None


class TestAuthServiceGetAdminByToken:
    def test_returns_admin_for_valid_admin_token(self) -> None:
        mock_admin_repo = MagicMock()
        admin = _make_admin_mock()
        mock_admin_repo.get_by_id.return_value = admin
        service = _make_service(mock_admin_repo)
        token = service.create_admin_token(admin)
        result = service.get_admin_by_token(token)
        assert result is admin

    def test_wrong_token_type_returns_none(self) -> None:
        service = _make_service()
        client = _make_oauth_client_mock()
        api_token, _ = service.create_api_token(client)
        result = service.get_admin_by_token(api_token)
        assert result is None

    def test_invalid_token_returns_none(self) -> None:
        service = _make_service()
        assert service.get_admin_by_token("invalid") is None


class TestAuthServiceGetApiClientByToken:
    def test_returns_client_for_valid_api_token(self) -> None:
        mock_oauth_repo = MagicMock()
        client = _make_oauth_client_mock()
        mock_oauth_repo.get_by_client_id.return_value = client
        service = _make_service(MagicMock(), mock_oauth_repo)
        token, _ = service.create_api_token(client)
        result = service.get_api_client_by_token(token)
        assert result is client

    def test_wrong_token_type_returns_none(self) -> None:
        service = _make_service()
        admin = _make_admin_mock()
        admin_token = service.create_admin_token(admin)
        result = service.get_api_client_by_token(admin_token)
        assert result is None


class TestAuthServiceAuthenticateAdmin:
    def test_returns_admin_with_correct_credentials(self) -> None:
        mock_admin_repo = MagicMock()
        admin = _make_admin_mock()
        mock_admin_repo.get_by_username.return_value = admin
        service = _make_service(mock_admin_repo)
        result = service.authenticate_admin("testadmin", "password123")
        assert result is admin

    def test_wrong_password(self) -> None:
        mock_admin_repo = MagicMock()
        admin = _make_admin_mock()
        mock_admin_repo.get_by_username.return_value = admin
        service = _make_service(mock_admin_repo)
        result = service.authenticate_admin("testadmin", "wrongpass")
        assert result is None

    def test_user_not_found(self) -> None:
        mock_admin_repo = MagicMock()
        mock_admin_repo.get_by_username.return_value = None
        service = _make_service(mock_admin_repo)
        result = service.authenticate_admin("nobody", "password123")
        assert result is None

    def test_inactive_admin(self) -> None:
        mock_admin_repo = MagicMock()
        admin = _make_admin_mock(status="inactive")
        mock_admin_repo.get_by_username.return_value = admin
        service = _make_service(mock_admin_repo)
        result = service.authenticate_admin("testadmin", "password123")
        assert result is None


class TestAuthServiceAuthenticateOAuthClient:
    def test_returns_client_with_correct_credentials(self) -> None:
        mock_oauth_repo = MagicMock()
        client = _make_oauth_client_mock()
        mock_oauth_repo.get_by_client_id.return_value = client
        service = _make_service(MagicMock(), mock_oauth_repo)
        result = service.authenticate_oauth_client("test_client_id", "test_secret")
        assert result is client

    def test_wrong_secret(self) -> None:
        mock_oauth_repo = MagicMock()
        client = _make_oauth_client_mock()
        mock_oauth_repo.get_by_client_id.return_value = client
        service = _make_service(MagicMock(), mock_oauth_repo)
        result = service.authenticate_oauth_client("test_client_id", "wrong_secret")
        assert result is None

    def test_client_not_found(self) -> None:
        mock_oauth_repo = MagicMock()
        mock_oauth_repo.get_by_client_id.return_value = None
        service = _make_service(MagicMock(), mock_oauth_repo)
        result = service.authenticate_oauth_client("nonexistent", "secret")
        assert result is None

    def test_inactive_client(self) -> None:
        mock_oauth_repo = MagicMock()
        client = _make_oauth_client_mock(status="inactive")
        mock_oauth_repo.get_by_client_id.return_value = client
        service = _make_service(MagicMock(), mock_oauth_repo)
        result = service.authenticate_oauth_client("test_client_id", "test_secret")
        assert result is None
