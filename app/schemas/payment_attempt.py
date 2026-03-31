from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


class PaymentAttemptCreate(BaseModel):
    order_id: int
    channel: Literal["alipay", "wechat", "stripe"]
    amount: int = Field(ge=0)


class PaymentAttemptMarkSuccess(BaseModel):
    channel_transaction_id: str


class PaymentAttemptResponse(BaseModel):
    id: int
    order_id: int
    channel: str
    amount: int
    status: str
    channel_transaction_id: str | None
    created_at: datetime
    updated_at: datetime | None

    model_config = {"from_attributes": True}
