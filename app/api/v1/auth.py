from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm

from app.api.deps import get_auth_service
from app.schemas.auth import OAuthTokenResponse, TokenResponse
from app.services.auth import AuthService

router = APIRouter(prefix="/auth", tags=["认证"])


@router.post("/login", response_model=TokenResponse)
def login(
    form: OAuth2PasswordRequestForm = Depends(),
    auth_service: AuthService = Depends(get_auth_service),
) -> TokenResponse:
    admin = auth_service.authenticate_admin(form.username, form.password)
    if admin is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="用户名或密码错误")
    token = auth_service.create_admin_token(admin)
    return TokenResponse(access_token=token)


@router.post("/api-token", response_model=OAuthTokenResponse)
def create_api_token(
    form: OAuth2PasswordRequestForm = Depends(),
    auth_service: AuthService = Depends(get_auth_service),
) -> OAuthTokenResponse:
    client = auth_service.authenticate_oauth_client(form.username, form.password)
    if client is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="无效的客户端凭据")
    token, expires_in = auth_service.create_api_token(client)
    return OAuthTokenResponse(access_token=token, expires_in=expires_in)
