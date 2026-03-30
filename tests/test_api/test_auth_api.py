"""Tests for Auth API endpoints."""

import bcrypt

from app.models.admin import Admin
from app.models.oauth_client import OAuthClient


def _insert_admin(db_session, *, username="loginadmin", password="pass123", role="admin", status="active") -> Admin:
    hashed = bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()
    admin = Admin(username=username, password_hash=hashed, role=role, status=status)
    db_session.add(admin)
    db_session.commit()
    db_session.refresh(admin)
    return admin


def _insert_oauth_client(db_session, *, client_id="test_cid", client_secret="test_cs", status="active") -> OAuthClient:
    hashed = bcrypt.hashpw(client_secret.encode(), bcrypt.gensalt()).decode()
    client = OAuthClient(client_id=client_id, client_secret=hashed, name="Test App", status=status)
    db_session.add(client)
    db_session.commit()
    db_session.refresh(client)
    return client


class TestLoginEndpoint:
    def test_login_success(self, client, db_session) -> None:
        _insert_admin(db_session, username="alice", password="secret123")
        resp = client.post("/api/v1/auth/login", data={"username": "alice", "password": "secret123"})
        assert resp.status_code == 200
        assert "access_token" in resp.json()

    def test_login_wrong_password(self, client, db_session) -> None:
        _insert_admin(db_session, username="alice", password="secret123")
        resp = client.post("/api/v1/auth/login", data={"username": "alice", "password": "wrong"})
        assert resp.status_code == 401

    def test_login_nonexistent_user(self, client) -> None:
        resp = client.post("/api/v1/auth/login", data={"username": "nobody", "password": "x"})
        assert resp.status_code == 401

    def test_login_inactive_admin(self, client, db_session) -> None:
        _insert_admin(db_session, username="alice", password="secret123", status="inactive")
        resp = client.post("/api/v1/auth/login", data={"username": "alice", "password": "secret123"})
        assert resp.status_code == 401


class TestCreateApiTokenEndpoint:
    def test_create_api_token_success(self, client, db_session) -> None:
        _insert_oauth_client(db_session, client_id="cid_1", client_secret="secret123")
        resp = client.post("/api/v1/auth/api-token", data={"username": "cid_1", "password": "secret123"})
        assert resp.status_code == 200
        data = resp.json()
        assert "access_token" in data
        assert "expires_in" in data

    def test_create_api_token_wrong_secret(self, client, db_session) -> None:
        _insert_oauth_client(db_session, client_id="cid_1", client_secret="secret123")
        resp = client.post("/api/v1/auth/api-token", data={"username": "cid_1", "password": "wrong"})
        assert resp.status_code == 401

    def test_create_api_token_nonexistent_client(self, client) -> None:
        resp = client.post("/api/v1/auth/api-token", data={"username": "nope", "password": "x"})
        assert resp.status_code == 401

    def test_create_api_token_inactive_client(self, client, db_session) -> None:
        _insert_oauth_client(db_session, client_id="cid_1", client_secret="secret123", status="inactive")
        resp = client.post("/api/v1/auth/api-token", data={"username": "cid_1", "password": "secret123"})
        assert resp.status_code == 401
