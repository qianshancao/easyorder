"""Tests for Auth API endpoints."""

import bcrypt
import jwt

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


class TestTokenTypeCrossUse:
    """测试 token 类型不能交叉使用。"""

    def test_api_token_rejected_by_admin_endpoint(self, client, api_client_token_headers) -> None:
        """API 客户端 token 不能访问 admin 端点。"""
        resp = client.get("/api/v1/subscriptions/admin/all", headers=api_client_token_headers)
        assert resp.status_code == 401

    def test_admin_token_rejected_by_api_client_endpoint(self, client, admin_token_headers) -> None:
        """Admin token 不能访问 API 客户端端点。"""
        resp = client.post(
            "/api/v1/subscriptions/",
            json={"external_user_id": "user_001", "plan_id": 1},
            headers=admin_token_headers,
        )
        assert resp.status_code == 401


class TestMalformedJwtTokens:
    """测试畸形 JWT token 被正确拒绝。"""

    def test_truncated_jwt_rejected(self, client, admin_token_headers) -> None:
        """截断的 JWT 应返回 401。"""
        token = admin_token_headers["Authorization"].split(" ")[1]
        bad_headers = {"Authorization": f"Bearer {token[:20]}"}
        resp = client.get("/api/v1/subscriptions/admin/all", headers=bad_headers)
        assert resp.status_code == 401

    def test_wrong_signing_key_rejected(self, client) -> None:
        """用错误密钥签名的 JWT 应返回 401。"""
        payload = {"sub": "1", "type": "admin", "exp": 9999999999}
        bad_token = jwt.encode(payload, "wrong_secret_key_here", algorithm="HS256")
        resp = client.get("/api/v1/subscriptions/admin/all", headers={"Authorization": f"Bearer {bad_token}"})
        assert resp.status_code == 401


class TestInactiveUserWithValidJwt:
    """测试用户停用后 JWT 仍被拒绝。"""

    def test_inactive_admin_with_valid_jwt_rejected(self, client, db_session) -> None:
        """Admin 停用后，已发放的 JWT 应被拒绝。"""
        admin = _insert_admin(db_session, username="to_disable", password="pass123")
        resp = client.post("/api/v1/auth/login", data={"username": "to_disable", "password": "pass123"})
        token = resp.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        # 停用 admin
        admin.status = "inactive"
        db_session.commit()

        resp = client.get("/api/v1/subscriptions/admin/all", headers=headers)
        assert resp.status_code == 401

    def test_inactive_oauth_client_with_valid_jwt_rejected(self, client, db_session) -> None:
        """OAuth 客户端停用后，已发放的 JWT 应被拒绝。"""
        oauth_client = _insert_oauth_client(db_session, client_id="to_disable", client_secret="secret123")
        resp = client.post("/api/v1/auth/api-token", data={"username": "to_disable", "password": "secret123"})
        token = resp.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        # 停用客户端
        oauth_client.status = "inactive"
        db_session.commit()

        resp = client.post(
            "/api/v1/orders/",
            json={"external_user_id": "user_001", "type": "one_time", "amount": 3000},
            headers=headers,
        )
        assert resp.status_code == 401
