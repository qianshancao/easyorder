from datetime import datetime

from pydantic import BaseModel


class SystemConfigCreate(BaseModel):
    key: str
    value: dict[str, object]
    description: str | None = None


class SystemConfigUpdate(BaseModel):
    value: dict[str, object] | None = None
    description: str | None = None


class SystemConfigResponse(BaseModel):
    id: int
    key: str
    value: dict[str, object]
    description: str | None
    updated_at: datetime | None

    model_config = {"from_attributes": True}
