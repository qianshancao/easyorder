"""Renewal-related schemas."""

from datetime import datetime

from pydantic import BaseModel


class RenewalAttemptResponse(BaseModel):
    """单次续费尝试的响应。"""

    subscription_id: int
    order_id: int | None
    success: bool
    error_message: str | None
    created_at: datetime

    model_config = {"from_attributes": True}


class RenewalBatchResponse(BaseModel):
    """批量续费操作的响应。"""

    processed_count: int
    success_count: int
    failure_count: int
    attempts: list[RenewalAttemptResponse]
