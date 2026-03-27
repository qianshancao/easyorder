from datetime import datetime

from pydantic import BaseModel


class PlanCreate(BaseModel):
    name: str
    cycle: str
    base_price: int
    introductory_price: int | None = None
    trial_price: int | None = None
    trial_duration: int | None = None
    features: dict[str, object] | None = None
    renewal_rules: dict[str, object] | None = None


class PlanResponse(BaseModel):
    id: int
    name: str
    cycle: str
    base_price: int
    introductory_price: int | None
    trial_price: int | None
    trial_duration: int | None
    features: dict[str, object] | None
    renewal_rules: dict[str, object] | None
    status: str
    created_at: datetime

    model_config = {"from_attributes": True}
