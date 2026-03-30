"""Tests for OAuthClientRepository."""

from app.models.oauth_client import OAuthClient


class TestOAuthClientRepositoryCreate:
    def test_create_client_success(self, oauth_client_repository) -> None:
        client = OAuthClient(client_id="cid_abc", client_secret="hashed_secret", name="My App")
        created = oauth_client_repository.create(client)
        assert created.id is not None
        assert created.client_id == "cid_abc"
        assert created.name == "My App"
        assert created.status == "active"


class TestOAuthClientRepositoryGetById:
    def test_get_by_id_found(self, oauth_client_repository) -> None:
        client = oauth_client_repository.create(OAuthClient(client_id="cid_1", client_secret="h", name="App"))
        result = oauth_client_repository.get_by_id(client.id)
        assert result is not None
        assert result.client_id == "cid_1"

    def test_get_by_id_not_found(self, oauth_client_repository) -> None:
        assert oauth_client_repository.get_by_id(999) is None


class TestOAuthClientRepositoryGetByClientId:
    def test_get_by_client_id_found(self, oauth_client_repository) -> None:
        oauth_client_repository.create(OAuthClient(client_id="cid_xyz", client_secret="h", name="App"))
        result = oauth_client_repository.get_by_client_id("cid_xyz")
        assert result is not None
        assert result.name == "App"

    def test_get_by_client_id_not_found(self, oauth_client_repository) -> None:
        assert oauth_client_repository.get_by_client_id("nonexistent") is None


class TestOAuthClientRepositoryListAll:
    def test_list_all_with_data(self, oauth_client_repository) -> None:
        oauth_client_repository.create(OAuthClient(client_id="c1", client_secret="h1", name="App1"))
        oauth_client_repository.create(OAuthClient(client_id="c2", client_secret="h2", name="App2"))
        result = oauth_client_repository.list_all()
        assert len(result) == 2
