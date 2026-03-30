from typing import NotRequired, TypedDict

from pydantic import BaseModel


class TokenPayload(TypedDict):
    sub: str
    type: str
    exp: int
    role: NotRequired[str]


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"  # noqa: S105


class OAuthTokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"  # noqa: S105
    expires_in: int
