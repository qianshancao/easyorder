from collections.abc import Generator
from typing import Annotated

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.admin import Admin
from app.models.oauth_client import OAuthClient
from app.repositories.admin import AdminRepository
from app.repositories.oauth_client import OAuthClientRepository
from app.repositories.order import OrderRepository
from app.repositories.payment_attempt import PaymentAttemptRepository
from app.repositories.plan import PlanRepository
from app.repositories.refund import RefundRepository
from app.repositories.subscription import SubscriptionRepository
from app.repositories.system_config import SystemConfigRepository
from app.schemas.auth import TokenPayload
from app.services.admin import AdminService
from app.services.auth import AuthService
from app.services.oauth_client import OAuthClientService
from app.services.order import OrderService
from app.services.payment_attempt import PaymentAttemptService
from app.services.plan import PlanService
from app.services.refund import RefundService
from app.services.subscription import SubscriptionService
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


def get_subscription_service(db: Session = Depends(get_db)) -> Generator[SubscriptionService, None, None]:
    yield SubscriptionService(SubscriptionRepository(db), PlanRepository(db))


def get_order_service(db: Session = Depends(get_db)) -> Generator[OrderService, None, None]:
    yield OrderService(OrderRepository(db), SubscriptionRepository(db))


def get_payment_attempt_service(db: Session = Depends(get_db)) -> Generator[PaymentAttemptService, None, None]:
    yield PaymentAttemptService(PaymentAttemptRepository(db), OrderRepository(db))


def get_refund_service(db: Session = Depends(get_db)) -> Generator[RefundService, None, None]:
    yield RefundService(RefundRepository(db), OrderRepository(db))


# ── 认证依赖 ──


def _verify_token_payload(
    token: str = Depends(_oauth2_scheme),
    auth_service: AuthService = Depends(get_auth_service),
) -> TokenPayload:
    payload = auth_service.verify_token(token)
    if payload is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="无效的认证令牌")
    return payload


def _get_current_admin(
    payload: TokenPayload = Depends(_verify_token_payload),
    db: Session = Depends(get_db),
) -> Admin:
    if payload["type"] != "admin":
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="无效的令牌类型")
    admin_id = int(payload["sub"])
    admin = AdminRepository(db).get_by_id(admin_id)
    if admin is None or admin.status != "active":
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="用户不存在或已禁用")
    return admin


def _require_super_admin(admin: Admin = Depends(_get_current_admin)) -> Admin:
    if admin.role != "super_admin":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="需要超级管理员权限")
    return admin


def _get_current_api_client(
    payload: TokenPayload = Depends(_verify_token_payload),
    db: Session = Depends(get_db),
) -> OAuthClient:
    if payload["type"] != "api":
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="无效的令牌类型")
    client_id = payload["sub"]
    client = OAuthClientRepository(db).get_by_client_id(client_id)
    if client is None or client.status != "active":
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="客户端不存在或已禁用")
    return client


# ── Annotated aliases (API routes use these to avoid importing models directly) ──

CurrentAdmin = Annotated[Admin, Depends(_get_current_admin)]
SuperAdmin = Annotated[Admin, Depends(_require_super_admin)]
CurrentApiClient = Annotated[OAuthClient, Depends(_get_current_api_client)]
