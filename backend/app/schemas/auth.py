from pydantic import BaseModel, EmailStr


class RegisterRequest(BaseModel):
    email: EmailStr
    display_name: str = ""
    password: str


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class UserResponse(BaseModel):
    id: str
    email: str
    display_name: str
    role: str
    household_id: str | None
    is_active: bool
    created_at: str

    model_config = {"from_attributes": True}
