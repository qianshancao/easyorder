from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.api.deps import CurrentAdmin, CurrentApiClient, get_payment_transaction_service
from app.schemas.payment_transaction import PaymentTransactionResponse
from app.services.payment_transaction import PaymentTransactionService

router = APIRouter(prefix="/payment-transactions", tags=["支付流水"])


# -- Admin API --


@router.get("/admin/all", response_model=list[PaymentTransactionResponse])
def admin_list_all(
    _admin: CurrentAdmin,
    payment_attempt_id: int | None = Query(default=None),
    order_id: int | None = Query(default=None),
    channel: str | None = Query(default=None),
    status: str | None = Query(default=None),
    limit: int = Query(default=100, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
    service: PaymentTransactionService = Depends(get_payment_transaction_service),
) -> list[PaymentTransactionResponse]:
    return [
        PaymentTransactionResponse.model_validate(t)
        for t in service.list_filtered(
            payment_attempt_id=payment_attempt_id,
            order_id=order_id,
            channel=channel,
            status=status,
            limit=limit,
            offset=offset,
        )
    ]


@router.get("/admin/{transaction_id}", response_model=PaymentTransactionResponse)
def admin_get_transaction(
    transaction_id: int,
    _admin: CurrentAdmin,
    service: PaymentTransactionService = Depends(get_payment_transaction_service),
) -> PaymentTransactionResponse:
    txn = service.get_transaction(transaction_id)
    if txn is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="支付流水不存在")
    return PaymentTransactionResponse.model_validate(txn)


# -- Business API --


@router.get("/by-attempt/{attempt_id}", response_model=list[PaymentTransactionResponse])
def list_by_attempt(
    attempt_id: int,
    _client: CurrentApiClient,
    service: PaymentTransactionService = Depends(get_payment_transaction_service),
) -> list[PaymentTransactionResponse]:
    return [PaymentTransactionResponse.model_validate(t) for t in service.list_by_attempt(attempt_id)]


@router.get("/by-order/{order_id}", response_model=list[PaymentTransactionResponse])
def list_by_order(
    order_id: int,
    _client: CurrentApiClient,
    service: PaymentTransactionService = Depends(get_payment_transaction_service),
) -> list[PaymentTransactionResponse]:
    return [PaymentTransactionResponse.model_validate(t) for t in service.list_by_order(order_id)]


@router.get("/{transaction_id}", response_model=PaymentTransactionResponse)
def get_transaction(
    transaction_id: int,
    _client: CurrentApiClient,
    service: PaymentTransactionService = Depends(get_payment_transaction_service),
) -> PaymentTransactionResponse:
    txn = service.get_transaction(transaction_id)
    if txn is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="支付流水不存在")
    return PaymentTransactionResponse.model_validate(txn)
