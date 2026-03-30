from collections.abc import Generator
from typing import Annotated

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from app.config import settings
from app.database import get_db
from app.models.admin import Admin
from app.models.oauth_client import OAuthClient
from app.repositories.admin import AdminRepository
from app.repositories.oauth_client import OAuthClientRepository
from app.repositories.plan import PlanRepository
from app.repositories.system_config import SystemConfigRepository
from app.services.admin import AdminService
from app.services.auth import AuthService
from app.services.oauth_client import OAuthClientService
from app.services.plan import PlanService
from app.services.system_config import SystemConfigService

_oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")


# ── Service 工厂 ──


def get_plan_service(db: Session = Depends(get_db)) -> Generator[PlanService, None, None]:
    repo = PlanRepository(db)
    yield PlanService(repo=repo)


def get_admin_service(db: Session = Depends(get_db)) -> Generator[AdminService, None, None]:
    repo = AdminRepository(db)
    yield AdminService(repo=repo)


def get_auth_service(db: Session = Depends(get_db)) -> Generator[AuthService, None, None]:
    yield AuthService(AdminRepository(db), OAuthClientRepository(db))


def get_system_config_service(db: Session = Depends(get_db)) -> Generator[SystemConfigService, None, None]:
    repo = SystemConfigRepository(db)
    yield SystemConfigService(repo=repo)


def get_oauth_client_service(db: Session = Depends(get_db)) -> Generator[OAuthClientService, None, None]:
    repo = OAuthClientRepository(db)
    yield OAuthClientService(repo=repo)


# ── 认证依赖 ──


def _get_current_admin(token: str = Depends(_oauth2_scheme)) -> Admin:
    try:
        payload = jwt.decode(token, settings.secret_key, algorithms=["HS256"])
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="无效的认证令牌") from None
    if payload.get("type") != "admin":
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="无效的令牌类型")
    admin_id = int(payload["sub"])  # type: ignore[arg-type]
    db = next(get_db())
    admin = AdminRepository(db).get_by_id(admin_id)
    if admin is None or admin.status != "active":
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="用户不存在或已禁用")
    return admin


def _require_super_admin(admin: Admin = Depends(_get_current_admin)) -> Admin:
    if admin.role != "super_admin":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="需要超级管理员权限")
    return admin


def _get_current_api_client(token: str = Depends(_oauth2_scheme)) -> OAuthClient:
    try:
        payload = jwt.decode(token, settings.secret_key, algorithms=["HS256"])
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="无效的认证令牌") from None
    if payload.get("type") != "api":
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="无效的令牌类型")
    client_id = str(payload["sub"])
    db = next(get_db())
    client = OAuthClientRepository(db).get_by_client_id(client_id)
    if client is None or client.status != "active":
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="客户端不存在或已禁用")
    return client


# ── Annotated aliases (API routes use these to avoid importing models directly) ──

CurrentAdmin = Annotated[Admin, Depends(_get_current_admin)]
SuperAdmin = Annotated[Admin, Depends(_require_super_admin)]
CurrentApiClient = Annotated[OAuthClient, Depends(_get_current_api_client)]
