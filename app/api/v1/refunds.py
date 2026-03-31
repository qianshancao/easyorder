from collections.abc import Callable

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field

from app.api.deps import CurrentAdmin, CurrentApiClient, get_refund_service
from app.models.refund import Refund
from app.schemas.refund import RefundCreate
from app.services.refund import RefundService

router = APIRouter(prefix="/refunds", tags=["退款"])


class RefundMarkSuccess(BaseModel):
    channel_refund_id: str = Field(max_length=128)


class RefundResponse(BaseModel):
    id: int
    order_id: int
    amount: int
    reason: str
    status: str
    channel: str
    channel_refund_id: str | None
    created_at: int
    updated_at: int | None
    completed_at: int | None

    @staticmethod
    def from_entity(obj: Refund) -> "RefundResponse":
        return RefundResponse(
            id=obj.id,
            order_id=obj.order_id,
            amount=obj.amount,
            reason=obj.reason,
            status=obj.status,
            channel=obj.channel,
            channel_refund_id=obj.channel_refund_id,
            created_at=int(obj.created_at.timestamp()),
            updated_at=int(obj.updated_at.timestamp()) if obj.updated_at else None,
            completed_at=int(obj.completed_at.timestamp()) if obj.completed_at else None,
        )


def _call_or_raise(service_fn: Callable[..., Refund | None], *args: object) -> RefundResponse:
    try:
        result = service_fn(*args)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc
    if result is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="退款不存在")
    return RefundResponse.from_entity(result)


# ── 管理 API (Admin 认证) ──


@router.get("/admin/all", response_model=list[RefundResponse])
def admin_list_all(
    _admin: CurrentAdmin,
    order_id: int | None = Query(default=None),
    status: str | None = Query(default=None),
    channel: str | None = Query(default=None),
    service: RefundService = Depends(get_refund_service),
) -> list[RefundResponse]:
    return [
        RefundResponse.from_entity(r)
        for r in service.list_refunds(
            order_id=order_id,
            status=status,
            channel=channel,
        )
    ]


@router.get("/admin/{refund_id}", response_model=RefundResponse)
def admin_get_refund(
    refund_id: int,
    _admin: CurrentAdmin,
    service: RefundService = Depends(get_refund_service),
) -> RefundResponse:
    refund = service.get_refund(refund_id)
    if refund is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="退款不存在")
    return RefundResponse.from_entity(refund)


# ── 业务 API (OAuth 客户端认证) ──


@router.post("/", response_model=RefundResponse, status_code=status.HTTP_201_CREATED)
def create_refund(
    data: RefundCreate,
    _client: CurrentApiClient,
    service: RefundService = Depends(get_refund_service),
) -> RefundResponse:
    try:
        refund = service.create_refund(data)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc
    return RefundResponse.from_entity(refund)


@router.get("/{refund_id}", response_model=RefundResponse)
def get_refund(
    refund_id: int,
    _client: CurrentApiClient,
    service: RefundService = Depends(get_refund_service),
) -> RefundResponse:
    refund = service.get_refund(refund_id)
    if refund is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="退款不存在")
    return RefundResponse.from_entity(refund)


@router.post("/{refund_id}/success", response_model=RefundResponse)
def mark_as_success(
    refund_id: int,
    data: RefundMarkSuccess,
    _client: CurrentApiClient,
    service: RefundService = Depends(get_refund_service),
) -> RefundResponse:
    return _call_or_raise(service.mark_success, refund_id, data.channel_refund_id)


@router.post("/{refund_id}/fail", response_model=RefundResponse)
def mark_as_failed(
    refund_id: int,
    _client: CurrentApiClient,
    service: RefundService = Depends(get_refund_service),
) -> RefundResponse:
    return _call_or_raise(service.mark_failed, refund_id)
