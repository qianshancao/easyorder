from fastapi import APIRouter, Depends, HTTPException, status

from app.api.deps import CurrentAdmin, CurrentApiClient, get_subscription_service
from app.schemas.order import OrderResponse
from app.schemas.subscription import (
    SubscriptionChangeRequest,
    SubscriptionChangeResponse,
    SubscriptionCreate,
    SubscriptionCreateResponse,
    SubscriptionResponse,
)
from app.services.subscription import SubscriptionService

router = APIRouter(prefix="/subscriptions", tags=["订阅"])


def _call_or_raise(service_fn, subscription_id: int) -> SubscriptionResponse:
    """Call a mutating service method, translating ValueError/None to HTTP errors."""
    try:
        sub = service_fn(subscription_id)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=str(exc)) from exc
    if sub is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="订阅不存在")
    return SubscriptionResponse.model_validate(sub)


# ── 管理 API (Admin 认证) ── 放在 /{id} 通配符前面


@router.get("/admin/all", response_model=list[SubscriptionResponse])
def admin_list_all(
    _admin: CurrentAdmin,
    service: SubscriptionService = Depends(get_subscription_service),
) -> list[SubscriptionResponse]:
    return [SubscriptionResponse.model_validate(s) for s in service.list_all()]


@router.get("/admin/{subscription_id}", response_model=SubscriptionResponse)
def admin_get_subscription(
    subscription_id: int,
    _admin: CurrentAdmin,
    service: SubscriptionService = Depends(get_subscription_service),
) -> SubscriptionResponse:
    sub = service.get_subscription(subscription_id)
    if sub is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="订阅不存在")
    return SubscriptionResponse.model_validate(sub)


@router.post("/admin/{subscription_id}/cancel", response_model=SubscriptionResponse)
def admin_cancel_subscription(
    subscription_id: int,
    _admin: CurrentAdmin,
    service: SubscriptionService = Depends(get_subscription_service),
) -> SubscriptionResponse:
    return _call_or_raise(service.cancel_subscription, subscription_id)


@router.post("/admin/{subscription_id}/reactivate", response_model=SubscriptionResponse)
def admin_reactivate_subscription(
    subscription_id: int,
    _admin: CurrentAdmin,
    service: SubscriptionService = Depends(get_subscription_service),
) -> SubscriptionResponse:
    return _call_or_raise(service.reactivate_subscription, subscription_id)


# ── 业务 API (OAuth 客户端认证) ──


@router.post("/", response_model=SubscriptionCreateResponse, status_code=status.HTTP_201_CREATED)
def create_subscription(
    data: SubscriptionCreate,
    _client: CurrentApiClient,
    service: SubscriptionService = Depends(get_subscription_service),
) -> SubscriptionCreateResponse:
    try:
        sub, order = service.create_subscription(data)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=str(exc)) from exc
    return SubscriptionCreateResponse(
        subscription=SubscriptionResponse.model_validate(sub),
        order=OrderResponse.model_validate(order),
    )


@router.get("/by-user/{external_user_id}", response_model=list[SubscriptionResponse])
def list_by_user(
    external_user_id: str,
    _client: CurrentApiClient,
    service: SubscriptionService = Depends(get_subscription_service),
) -> list[SubscriptionResponse]:
    return [SubscriptionResponse.model_validate(s) for s in service.list_by_external_user_id(external_user_id)]


@router.get("/{subscription_id}", response_model=SubscriptionResponse)
def get_subscription(
    subscription_id: int,
    _client: CurrentApiClient,
    service: SubscriptionService = Depends(get_subscription_service),
) -> SubscriptionResponse:
    sub = service.get_subscription(subscription_id)
    if sub is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="订阅不存在")
    return SubscriptionResponse.model_validate(sub)


@router.post("/{subscription_id}/cancel", response_model=SubscriptionResponse)
def cancel_subscription(
    subscription_id: int,
    _client: CurrentApiClient,
    service: SubscriptionService = Depends(get_subscription_service),
) -> SubscriptionResponse:
    return _call_or_raise(service.cancel_subscription, subscription_id)


@router.post("/{subscription_id}/upgrade", response_model=SubscriptionChangeResponse)
def upgrade_subscription(
    subscription_id: int,
    data: SubscriptionChangeRequest,
    _client: CurrentApiClient,
    service: SubscriptionService = Depends(get_subscription_service),
) -> SubscriptionChangeResponse:
    try:
        sub, order = service.upgrade_subscription(subscription_id, data.new_plan_id)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=str(exc)) from exc
    return SubscriptionChangeResponse(
        subscription=SubscriptionResponse.model_validate(sub),
        order=OrderResponse.model_validate(order),
        proration_amount=order.amount,
    )


@router.post("/{subscription_id}/downgrade", response_model=SubscriptionChangeResponse)
def downgrade_subscription(
    subscription_id: int,
    data: SubscriptionChangeRequest,
    _client: CurrentApiClient,
    service: SubscriptionService = Depends(get_subscription_service),
) -> SubscriptionChangeResponse:
    try:
        sub, order = service.downgrade_subscription(subscription_id, data.new_plan_id)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=str(exc)) from exc
    return SubscriptionChangeResponse(
        subscription=SubscriptionResponse.model_validate(sub),
        order=OrderResponse.model_validate(order),
        proration_amount=order.amount,
    )
