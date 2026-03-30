from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.oauth_client import OAuthClient
from app.repositories.base import BaseRepository


class OAuthClientRepository(BaseRepository[OAuthClient]):
    def __init__(self, db: Session) -> None:
        super().__init__(OAuthClient, db)

    def get_by_client_id(self, client_id: str) -> OAuthClient | None:
        stmt = select(OAuthClient).where(OAuthClient.client_id == client_id)
        return self.db.execute(stmt).scalar_one_or_none()
