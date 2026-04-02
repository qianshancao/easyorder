"""Tests for OAuthClientService."""

import bcrypt

from app.schemas.oauth_client import OAuthClientCreate
from app.services.oauth_client import OAuthClientService

from .conftest import _make_oauth_client_mock as _make_client_mock


class TestOAuthClientServiceCreateClient:
    def test_returns_client_and_raw_secret(self, mock_oauth_client_repository) -> None:
        mock_oauth_client_repository.create.side_effect = lambda e: e
        service = OAuthClientService(mock_oauth_client_repository)
        client, raw_secret = service.create_client(OAuthClientCreate(name="My App"))
        assert client.name == "My App"
        assert isinstance(raw_secret, str)
        assert len(raw_secret) > 0

    def test_client_secret_is_hashed_not_plaintext(self, mock_oauth_client_repository) -> None:
        mock_oauth_client_repository.create.side_effect = lambda e: e
        service = OAuthClientService(mock_oauth_client_repository)
        client, raw_secret = service.create_client(OAuthClientCreate(name="App"))
        # ORM stored hash should differ from raw secret
        assert client.client_secret != raw_secret
        # Hash should be verifiable with bcrypt
        assert bcrypt.checkpw(raw_secret.encode(), client.client_secret.encode())


class TestOAuthClientServiceRegenerateSecret:
    def test_success(self, mock_oauth_client_repository) -> None:
        existing = _make_client_mock(client_secret="old_hash")
        mock_oauth_client_repository.get_by_id.return_value = existing
        mock_oauth_client_repository.update.side_effect = lambda e: e
        service = OAuthClientService(mock_oauth_client_repository)
        client, raw_secret = service.regenerate_secret(1)
        assert client is not None
        assert raw_secret is not None
        assert client.client_secret != "old_hash"

    def test_not_found(self, mock_oauth_client_repository) -> None:
        mock_oauth_client_repository.get_by_id.return_value = None
        service = OAuthClientService(mock_oauth_client_repository)
        client, raw_secret = service.regenerate_secret(999)
        assert client is None
        assert raw_secret is None


class TestOAuthClientServiceUpdateStatus:
    def test_success(self, mock_oauth_client_repository) -> None:
        client = _make_client_mock(status="active")
        mock_oauth_client_repository.get_by_id.return_value = client
        mock_oauth_client_repository.update.side_effect = lambda e: e
        service = OAuthClientService(mock_oauth_client_repository)
        result = service.update_status(1, "inactive")
        assert result is not None
        assert result.status == "inactive"

    def test_not_found(self, mock_oauth_client_repository) -> None:
        mock_oauth_client_repository.get_by_id.return_value = None
        service = OAuthClientService(mock_oauth_client_repository)
        result = service.update_status(999, "inactive")
        assert result is None
