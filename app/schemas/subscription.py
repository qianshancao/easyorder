from datetime import datetime

from pydantic import BaseModel


class SubscriptionCreate(BaseModel):
    external_user_id: str
    plan_id: int


class SubscriptionResponse(BaseModel):
    id: int
    external_user_id: str
    plan_id: int
    plan_snapshot: dict[str, object]
    status: str
    current_period_start: datetime
    current_period_end: datetime
    canceled_at: datetime | None
    created_at: datetime

    model_config = {"from_attributes": True}
