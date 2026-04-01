from fastapi import Cookie, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.exceptions import AuthenticationError
from app.models.user import User
from app.services.auth import AuthService


async def get_current_user(
    session_id: str | None = Cookie(default=None),
    db: AsyncSession = Depends(get_db),
) -> User:
    if not session_id:
        raise AuthenticationError("Not authenticated", code="NOT_AUTHENTICATED")

    svc = AuthService(db)
    user = await svc.get_current_user(session_id)
    if not user:
        raise AuthenticationError("Invalid or expired session", code="INVALID_SESSION")

    return user


def require_admin(user: User = Depends(get_current_user)) -> User:
    from app.core.exceptions import ForbiddenError

    if user.role != "admin":
        raise ForbiddenError("Admin access required", code="ADMIN_REQUIRED")
    return user
