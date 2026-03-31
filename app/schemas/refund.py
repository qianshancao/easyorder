from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


class RefundCreate(BaseModel):
    order_id: int
    amount: int = Field(ge=0)
    reason: str = Field(min_length=1)
    channel: Literal["alipay", "wechat", "stripe"]


class RefundUpdate(BaseModel):
    status: Literal["pending", "success", "failed"] | None = None
    channel_refund_id: str | None = Field(default=None, max_length=128)
    completed_at: datetime | None = None


class RefundResponse(BaseModel):
    id: int
    order_id: int
    amount: int
    reason: str
    status: str
    channel: str
    channel_refund_id: str | None
    created_at: datetime
    updated_at: datetime | None
    completed_at: datetime | None

    model_config = {"from_attributes": True}
