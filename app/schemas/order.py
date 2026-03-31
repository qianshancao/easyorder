from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


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
