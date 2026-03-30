import logging
from datetime import UTC, datetime, timedelta

import bcrypt
import jwt

from app.config import settings
from app.models.admin import Admin
from app.models.oauth_client import OAuthClient
from app.repositories.admin import AdminRepository
from app.repositories.oauth_client import OAuthClientRepository

logger = logging.getLogger(__name__)


class AuthService:
    def __init__(self, admin_repo: AdminRepository, oauth_client_repo: OAuthClientRepository) -> None:
        self.admin_repo = admin_repo
        self.oauth_client_repo = oauth_client_repo

    def create_admin_token(self, admin: Admin) -> str:
        expire = datetime.now(tz=UTC) + timedelta(minutes=settings.admin_jwt_expire_minutes)
        payload = {
            "sub": str(admin.id),
            "role": admin.role,
            "type": "admin",
            "exp": expire,
        }
        return jwt.encode(payload, settings.secret_key, algorithm="HS256")

    def create_api_token(self, client: OAuthClient) -> tuple[str, int]:
        expire = datetime.now(tz=UTC) + timedelta(seconds=settings.api_token_expire_seconds)
        payload = {
            "sub": client.client_id,
            "type": "api",
            "exp": expire,
        }
        token = jwt.encode(payload, settings.secret_key, algorithm="HS256")
        return token, settings.api_token_expire_seconds

    def verify_token(self, token: str) -> dict[str, object] | None:
        try:
            return jwt.decode(token, settings.secret_key, algorithms=["HS256"])
        except jwt.ExpiredSignatureError:
            logger.info("auth.token_expired")
            return None
        except jwt.InvalidTokenError:
            logger.info("auth.token_invalid")
            return None

    def get_admin_by_token(self, token: str) -> Admin | None:
        payload = self.verify_token(token)
        if payload is None or payload.get("type") != "admin":
            return None
        admin_id = int(payload["sub"])  # type: ignore[arg-type]
        return self.admin_repo.get_by_id(admin_id)

    def get_api_client_by_token(self, token: str) -> OAuthClient | None:
        payload = self.verify_token(token)
        if payload is None or payload.get("type") != "api":
            return None
        client_id = str(payload["sub"])
        return self.oauth_client_repo.get_by_client_id(client_id)

    def authenticate_admin(self, username: str, password: str) -> Admin | None:
        admin = self.admin_repo.get_by_username(username)
        if admin is None:
            return None
        if not bcrypt.checkpw(password.encode(), admin.password_hash.encode()):
            return None
        if admin.status != "active":
            return None
        return admin

    def authenticate_oauth_client(self, client_id: str, client_secret: str) -> OAuthClient | None:
        client = self.oauth_client_repo.get_by_client_id(client_id)
        if client is None:
            return None
        if not bcrypt.checkpw(client_secret.encode(), client.client_secret.encode()):
            return None
        if client.status != "active":
            return None
        return client
