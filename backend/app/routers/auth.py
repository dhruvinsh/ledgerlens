from fastapi import APIRouter, Depends, Request, Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.models.user import User
from app.schemas.auth import LoginRequest, RegisterRequest, UserResponse
from app.services.auth import SESSION_MAX_AGE_DAYS, AuthService

router = APIRouter(prefix="/auth", tags=["auth"])

COOKIE_MAX_AGE = SESSION_MAX_AGE_DAYS * 24 * 3600


def _set_session_cookie(response: Response, token: str) -> None:
    response.set_cookie(
        key="session_id",
        value=token,
        max_age=COOKIE_MAX_AGE,
        httponly=True,
        samesite="lax",
        secure=False,  # Set True behind HTTPS in production
    )


def _to_user_response(user: User) -> UserResponse:
    return UserResponse(
        id=user.id,
        email=user.email,
        display_name=user.display_name,
        role=user.role,
        household_id=user.household_id,
        is_active=user.is_active,
        created_at=user.created_at.isoformat(),
    )


@router.post("/register", response_model=UserResponse, status_code=201)
async def register(
    body: RegisterRequest,
    request: Request,
    response: Response,
    db: AsyncSession = Depends(get_db),
) -> UserResponse:
    svc = AuthService(db)
    user, token = await svc.register(
        email=body.email,
        display_name=body.display_name,
        password=body.password,
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
    )
    _set_session_cookie(response, token)
    return _to_user_response(user)


@router.post("/login", response_model=UserResponse)
async def login(
    body: LoginRequest,
    request: Request,
    response: Response,
    db: AsyncSession = Depends(get_db),
) -> UserResponse:
    svc = AuthService(db)
    user, token = await svc.login(
        email=body.email,
        password=body.password,
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
    )
    _set_session_cookie(response, token)
    return _to_user_response(user)


@router.post("/logout", status_code=200)
async def logout(
    request: Request,
    response: Response,
    db: AsyncSession = Depends(get_db),
) -> dict[str, str]:
    token = request.cookies.get("session_id")
    if token:
        svc = AuthService(db)
        await svc.logout(token)
    response.delete_cookie("session_id")
    return {"detail": "Logged out"}


@router.get("/me", response_model=UserResponse)
async def me(user: User = Depends(get_current_user)) -> UserResponse:
    return _to_user_response(user)
