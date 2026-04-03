from datetime import datetime

from pydantic import BaseModel, Field


class PaymentTransactionCreate(BaseModel):
    """内部使用的创建 schema，不直接暴露 API。"""

    payment_attempt_id: int
    order_id: int
    channel: str
    amount: int = Field(ge=0)
    currency: str = Field(default="CNY", max_length=3)
    channel_transaction_id: str
    raw_callback_data: str | None = None


class PaymentTransactionResponse(BaseModel):
    id: int
    payment_attempt_id: int
    order_id: int
    channel: str
    amount: int
    currency: str
    channel_transaction_id: str
    raw_callback_data: str | None
    status: str
    created_at: datetime
    updated_at: datetime | None

    model_config = {"from_attributes": True}
