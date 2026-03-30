from datetime import datetime

from pydantic import BaseModel


class OAuthClientCreate(BaseModel):
    name: str


class OAuthClientResponse(BaseModel):
    id: int
    client_id: str
    name: str
    status: str
    created_at: datetime

    model_config = {"from_attributes": True}


class OAuthClientSecretResponse(BaseModel):
    client_id: str
    client_secret: str
