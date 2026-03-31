from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.api.deps import (
    CurrentAdmin,
    CurrentApiClient,
    get_order_service,
    get_payment_attempt_service,
)
from app.schemas.order import (
    OneTimePurchaseRequest,
    OneTimePurchaseResponse,
    OrderCreate,
    OrderResponse,
)
from app.schemas.payment_attempt import PaymentAttemptCreate, PaymentAttemptResponse
from app.services.order import OrderService
from app.services.payment_attempt import PaymentAttemptService

router = APIRouter(prefix="/orders", tags=["订单"])


def _call_or_raise(service_fn, order_id: int) -> OrderResponse:
    try:
        order = service_fn(order_id)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=str(exc)) from exc
    if order is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="订单不存在")
    return OrderResponse.model_validate(order)


# ── 管理 API (Admin 认证) ──


@router.get("/admin/all", response_model=list[OrderResponse])
def admin_list_all(
    _admin: CurrentAdmin,
    status: str | None = Query(default=None),
    order_type: str | None = Query(default=None, alias="type"),
    external_user_id: str | None = Query(default=None),
    subscription_id: int | None = Query(default=None),
    service: OrderService = Depends(get_order_service),
) -> list[OrderResponse]:
    return [
        OrderResponse.model_validate(o)
        for o in service.list_filtered(
            status=status,
            order_type=order_type,
            external_user_id=external_user_id,
            subscription_id=subscription_id,
        )
    ]


@router.get("/admin/{order_id}", response_model=OrderResponse)
def admin_get_order(
    order_id: int,
    _admin: CurrentAdmin,
    service: OrderService = Depends(get_order_service),
) -> OrderResponse:
    order = service.get_order(order_id)
    if order is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="订单不存在")
    return OrderResponse.model_validate(order)


@router.post("/admin/{order_id}/cancel", response_model=OrderResponse)
def admin_cancel_order(
    order_id: int,
    _admin: CurrentAdmin,
    service: OrderService = Depends(get_order_service),
) -> OrderResponse:
    return _call_or_raise(service.mark_as_canceled, order_id)


# ── 业务 API (OAuth 客户端认证) ──


@router.post("/", response_model=OrderResponse, status_code=status.HTTP_201_CREATED)
def create_order(
    data: OrderCreate,
    _client: CurrentApiClient,
    service: OrderService = Depends(get_order_service),
) -> OrderResponse:
    if data.type != "one_time":
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="业务 API 仅支持创建 one_time 类型订单",
        )
    try:
        order = service.create_order(data)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=str(exc)) from exc
    return OrderResponse.model_validate(order)


@router.post("/one-time-pay", response_model=OneTimePurchaseResponse)
def one_time_purchase(
    data: OneTimePurchaseRequest,
    _client: CurrentApiClient,
    service: OrderService = Depends(get_order_service),
    pa_service: PaymentAttemptService = Depends(get_payment_attempt_service),
) -> OneTimePurchaseResponse:
    try:
        order = service.create_order(
            OrderCreate(
                external_user_id=data.external_user_id,
                type="one_time",
                amount=data.amount,
                currency=data.currency,
            )
        )
        attempt = pa_service.create_attempt(
            PaymentAttemptCreate(
                order_id=order.id,
                channel=data.channel,
                amount=data.amount,
            )
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=str(exc)) from exc
    return OneTimePurchaseResponse(
        order=OrderResponse.model_validate(order),
        payment_attempt=PaymentAttemptResponse.model_validate(attempt),
    )


@router.get("/by-user/{external_user_id}", response_model=list[OrderResponse])
def list_by_user(
    external_user_id: str,
    _client: CurrentApiClient,
    service: OrderService = Depends(get_order_service),
) -> list[OrderResponse]:
    return [OrderResponse.model_validate(o) for o in service.list_by_external_user_id(external_user_id)]


@router.get("/by-subscription/{subscription_id}", response_model=list[OrderResponse])
def list_by_subscription(
    subscription_id: int,
    _client: CurrentApiClient,
    service: OrderService = Depends(get_order_service),
) -> list[OrderResponse]:
    return [OrderResponse.model_validate(o) for o in service.list_by_subscription_id(subscription_id)]


@router.get("/{order_id}", response_model=OrderResponse)
def get_order(
    order_id: int,
    _client: CurrentApiClient,
    service: OrderService = Depends(get_order_service),
) -> OrderResponse:
    order = service.get_order(order_id)
    if order is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="订单不存在")
    return OrderResponse.model_validate(order)


@router.post("/{order_id}/pay", response_model=OrderResponse)
def mark_as_paid(
    order_id: int,
    _client: CurrentApiClient,
    service: OrderService = Depends(get_order_service),
) -> OrderResponse:
    return _call_or_raise(service.mark_as_paid, order_id)


@router.post("/{order_id}/cancel", response_model=OrderResponse)
def cancel_order(
    order_id: int,
    _client: CurrentApiClient,
    service: OrderService = Depends(get_order_service),
) -> OrderResponse:
    return _call_or_raise(service.mark_as_canceled, order_id)
