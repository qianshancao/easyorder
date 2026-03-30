import logging
import secrets

import bcrypt

from app.models.oauth_client import OAuthClient
from app.repositories.oauth_client import OAuthClientRepository
from app.schemas.oauth_client import OAuthClientCreate
from app.services.base import BaseService

logger = logging.getLogger(__name__)


def _hash_secret(secret: str) -> str:
    return bcrypt.hashpw(secret.encode(), bcrypt.gensalt()).decode()


class OAuthClientService(BaseService[OAuthClient]):
    def __init__(self, repo: OAuthClientRepository) -> None:
        super().__init__(repo, domain_name="oauth_client")

    def create_client(self, data: OAuthClientCreate) -> tuple[OAuthClient, str]:
        raw_secret = secrets.token_urlsafe(48)
        client = OAuthClient(
            client_id=secrets.token_urlsafe(32),
            client_secret=_hash_secret(raw_secret),
            name=data.name,
        )
        created = self.repo.create(client)
        logger.info(
            "oauth_client.created",
            extra={"client_id": created.client_id, "client_name": created.name},
        )
        return created, raw_secret

    def regenerate_secret(self, client_id: int) -> tuple[OAuthClient | None, str | None]:
        client = self.repo.get_by_id(client_id)
        if client is None:
            return None, None
        raw_secret = secrets.token_urlsafe(48)
        client.client_secret = _hash_secret(raw_secret)
        updated = self.repo.update(client)
        logger.info("oauth_client.secret_regenerated", extra={"client_id": updated.client_id})
        return updated, raw_secret

    def update_status(self, client_id: int, status: str) -> OAuthClient | None:
        client = self.repo.get_by_id(client_id)
        if client is None:
            return None
        client.status = status
        updated = self.repo.update(client)
        logger.info("oauth_client.status_updated", extra={"client_id": updated.client_id, "status": status})
        return updated
