from collections.abc import Callable

from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.api.deps import CurrentAdmin, CurrentApiClient, get_payment_attempt_service
from app.models.payment_attempt import PaymentAttempt
from app.schemas.payment_attempt import (
    PaymentAttemptCreate,
    PaymentAttemptMarkSuccess,
    PaymentAttemptResponse,
)
from app.services.payment_attempt import PaymentAttemptService

router = APIRouter(prefix="/payment-attempts", tags=["支付尝试"])


def _call_or_raise(service_fn: Callable[..., PaymentAttempt | None], *args: object) -> PaymentAttemptResponse:
    try:
        result = service_fn(*args)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=str(exc)) from exc
    if result is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="支付尝试不存在")
    return PaymentAttemptResponse.model_validate(result)


# ── 管理 API (Admin 认证) ──


@router.get("/admin/all", response_model=list[PaymentAttemptResponse])
def admin_list_all(
    _admin: CurrentAdmin,
    order_id: int | None = Query(default=None),
    channel: str | None = Query(default=None),
    status: str | None = Query(default=None),
    limit: int = Query(default=100, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
    service: PaymentAttemptService = Depends(get_payment_attempt_service),
) -> list[PaymentAttemptResponse]:
    return [
        PaymentAttemptResponse.model_validate(a)
        for a in service.list_filtered(
            order_id=order_id,
            channel=channel,
            status=status,
            limit=limit,
            offset=offset,
        )
    ]


@router.get("/admin/{attempt_id}", response_model=PaymentAttemptResponse)
def admin_get_attempt(
    attempt_id: int,
    _admin: CurrentAdmin,
    service: PaymentAttemptService = Depends(get_payment_attempt_service),
) -> PaymentAttemptResponse:
    attempt = service.get_attempt(attempt_id)
    if attempt is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="支付尝试不存在")
    return PaymentAttemptResponse.model_validate(attempt)


# ── 业务 API (OAuth 客户端认证) ──


@router.post("/", response_model=PaymentAttemptResponse, status_code=status.HTTP_201_CREATED)
def create_attempt(
    data: PaymentAttemptCreate,
    _client: CurrentApiClient,
    service: PaymentAttemptService = Depends(get_payment_attempt_service),
) -> PaymentAttemptResponse:
    try:
        attempt = service.create_attempt(data)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=str(exc)) from exc
    return PaymentAttemptResponse.model_validate(attempt)


@router.get("/by-order/{order_id}", response_model=list[PaymentAttemptResponse])
def list_by_order(
    order_id: int,
    _client: CurrentApiClient,
    service: PaymentAttemptService = Depends(get_payment_attempt_service),
) -> list[PaymentAttemptResponse]:
    return [PaymentAttemptResponse.model_validate(a) for a in service.list_by_order(order_id)]


@router.get("/{attempt_id}", response_model=PaymentAttemptResponse)
def get_attempt(
    attempt_id: int,
    _client: CurrentApiClient,
    service: PaymentAttemptService = Depends(get_payment_attempt_service),
) -> PaymentAttemptResponse:
    attempt = service.get_attempt(attempt_id)
    if attempt is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="支付尝试不存在")
    return PaymentAttemptResponse.model_validate(attempt)


@router.post("/{attempt_id}/success", response_model=PaymentAttemptResponse)
def mark_as_success(
    attempt_id: int,
    data: PaymentAttemptMarkSuccess,
    _client: CurrentApiClient,
    service: PaymentAttemptService = Depends(get_payment_attempt_service),
) -> PaymentAttemptResponse:
    return _call_or_raise(service.mark_as_success, attempt_id, data.channel_transaction_id)


@router.post("/{attempt_id}/fail", response_model=PaymentAttemptResponse)
def mark_as_failed(
    attempt_id: int,
    _client: CurrentApiClient,
    service: PaymentAttemptService = Depends(get_payment_attempt_service),
) -> PaymentAttemptResponse:
    return _call_or_raise(service.mark_as_failed, attempt_id)
