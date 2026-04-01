from pydantic import BaseModel

from app.schemas.auth import UserResponse


class HouseholdCreate(BaseModel):
    name: str


class HouseholdUpdate(BaseModel):
    name: str | None = None
    sharing_mode: str | None = None


class HouseholdResponse(BaseModel):
    id: str
    name: str
    owner_id: str
    sharing_mode: str
    users: list[UserResponse]
    created_at: str

    model_config = {"from_attributes": True}


class InviteResponse(BaseModel):
    invite_url: str
    token: str
