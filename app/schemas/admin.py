from datetime import datetime

from pydantic import BaseModel


class AdminCreate(BaseModel):
    username: str
    password: str
    display_name: str | None = None
    role: str = "admin"


class AdminUpdate(BaseModel):
    display_name: str | None = None
    role: str | None = None
    status: str | None = None


class PasswordChange(BaseModel):
    old_password: str
    new_password: str


class AdminResponse(BaseModel):
    id: int
    username: str
    display_name: str | None
    role: str
    status: str
    created_at: datetime

    model_config = {"from_attributes": True}
