"""自动续费 API 路由。"""

from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.api.deps import CurrentApiClient, SuperAdmin, get_renewal_service
from app.schemas.renewal import RenewalBatchResponse
from app.schemas.subscription import SubscriptionResponse
from app.services.renewal import RenewalService

router = APIRouter(prefix="/renewals", tags=["自动续费"])


# ── 管理 API (SuperAdmin 认证) ──


@router.post("/admin/process", response_model=RenewalBatchResponse)
def admin_process_renewals(
    _admin: SuperAdmin,
    service: RenewalService = Depends(get_renewal_service),
    grace_period_days: int = Query(default=7, ge=1, le=30, description="提前多少天开始处理续费"),
) -> RenewalBatchResponse:
    """批量处理即将到期的订阅，创建续费订单和支付尝试。"""
    return service.process_renewals(grace_period_days=grace_period_days)


@router.post("/admin/{subscription_id}/success", response_model=SubscriptionResponse)
def admin_mark_renewal_success(
    subscription_id: int,
    _admin: SuperAdmin,
    service: RenewalService = Depends(get_renewal_service),
) -> SubscriptionResponse:
    """标记续费成功，延长订阅周期。"""
    result = service.handle_renewal_success(subscription_id)
    if result is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Subscription {subscription_id} not found",
        )
    return SubscriptionResponse.model_validate(result)


@router.post("/admin/{subscription_id}/fail", response_model=SubscriptionResponse)
def admin_mark_renewal_failure(
    subscription_id: int,
    _admin: SuperAdmin,
    service: RenewalService = Depends(get_renewal_service),
    grace_period_days: int = Query(default=7, ge=1, le=30, description="宽限期天数"),
) -> SubscriptionResponse:
    """标记续费失败，将订阅设为 past_due 状态。"""
    result = service.handle_renewal_failure(subscription_id, grace_period_days=grace_period_days)
    if result is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Subscription {subscription_id} not found",
        )
    return SubscriptionResponse.model_validate(result)


@router.post("/admin/process-expired")
def admin_process_expired(
    _admin: SuperAdmin,
    service: RenewalService = Depends(get_renewal_service),
    grace_period_days: int = Query(default=7, ge=1, le=30, description="宽限期天数"),
) -> dict[str, int]:
    """处理过期的订阅，将 past_due 且超过宽限期的订阅设为 expired。"""
    expired_count = service.process_expired_subscriptions(grace_period_days=grace_period_days)
    return {"expired_count": expired_count}


# ── 业务 API (OAuth 客户端认证) ──


@router.post("/{subscription_id}/renew")
def client_renew_subscription(
    subscription_id: int,
    _client: CurrentApiClient,
    service: RenewalService = Depends(get_renewal_service),
) -> dict[str, object]:
    """为单个订阅创建续费订单。

    如果订阅已取消或不存在，返回错误。
    """
    result = service.renew_subscription(subscription_id)
    error_msg = result.error_message or ""
    if not result.success and "not found" in error_msg.lower():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=error_msg,
        )
    return {
        "subscription_id": result.subscription_id,
        "order_id": result.order_id,
        "success": result.success,
        "error_message": result.error_message,
        "created_at": result.created_at.isoformat(),
    }
