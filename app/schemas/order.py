from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

from app.schemas.payment_attempt import PaymentAttemptResponse


class OrderCreate(BaseModel):
    external_user_id: str
    subscription_id: int | None = None
    type: Literal["opening", "renewal", "upgrade", "downgrade", "one_time"]
    amount: int = Field(ge=0)
    currency: str = Field(default="CNY", max_length=3)


class OrderResponse(BaseModel):
    id: int
    external_user_id: str
    subscription_id: int | None
    type: str
    amount: int
    currency: str
    status: str
    created_at: datetime
    updated_at: datetime | None
    paid_at: datetime | None
    canceled_at: datetime | None

    model_config = {"from_attributes": True}


class OneTimePurchaseRequest(BaseModel):
    external_user_id: str
    amount: int = Field(gt=0)
    currency: str = Field(default="CNY", max_length=3)
    channel: Literal["alipay", "wechat", "stripe"]


class OneTimePurchaseResponse(BaseModel):
    order: OrderResponse
    payment_attempt: PaymentAttemptResponse
