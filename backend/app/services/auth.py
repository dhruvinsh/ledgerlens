import uuid
from datetime import timedelta

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import DuplicateEmailError, InvalidCredentialsError
from app.core.security import (
    create_session_token,
    hash_password,
    verify_password,
    verify_session_token,
)
from app.core.time import utc_now
from app.models.user import User
from app.models.user_session import UserSession
from app.repositories.session import SessionRepository
from app.repositories.user import UserRepository

SESSION_MAX_AGE_DAYS = 30


class AuthService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.user_repo = UserRepository(db)
        self.session_repo = SessionRepository(db)

    async def register(
        self,
        email: str,
        display_name: str,
        password: str,
        ip_address: str | None = None,
        user_agent: str | None = None,
    ) -> tuple[User, str]:
        existing = await self.user_repo.get_by_email(email)
        if existing:
            raise DuplicateEmailError("Email already registered", code="DUPLICATE_EMAIL")

        # First user becomes admin
        user_count = await self.user_repo.count()
        role = "admin" if user_count == 0 else "member"

        user = User(
            email=email,
            display_name=display_name,
            password_hash=hash_password(password),
            role=role,
        )
        await self.user_repo.create(user)

        token = await self._create_session(user.id, ip_address, user_agent)
        await self.db.commit()
        return user, token

    async def login(
        self,
        email: str,
        password: str,
        ip_address: str | None = None,
        user_agent: str | None = None,
    ) -> tuple[User, str]:
        user = await self.user_repo.get_by_email(email)
        if not user or not verify_password(password, user.password_hash):
            raise InvalidCredentialsError(
                "Invalid email or password", code="INVALID_CREDENTIALS"
            )

        if not user.is_active:
            raise InvalidCredentialsError(
                "Account is deactivated", code="ACCOUNT_INACTIVE"
            )

        token = await self._create_session(user.id, ip_address, user_agent)
        await self.db.commit()
        return user, token

    async def logout(self, session_token: str) -> None:
        session_id = verify_session_token(session_token)
        if session_id:
            await self.session_repo.delete_by_id(session_id)
            await self.db.commit()

    async def get_current_user(self, session_token: str) -> User | None:
        session_id = verify_session_token(session_token)
        if not session_id:
            return None

        session = await self.session_repo.get_by_id(session_id)
        if not session:
            return None

        user = await self.user_repo.get_by_id(session.user_id)
        if not user or not user.is_active:
            return None

        return user

    async def _create_session(
        self,
        user_id: str,
        ip_address: str | None,
        user_agent: str | None,
    ) -> str:
        session_id = str(uuid.uuid4())
        session = UserSession(
            id=session_id,
            user_id=user_id,
            expires_at=utc_now() + timedelta(days=SESSION_MAX_AGE_DAYS),
            ip_address=ip_address,
            user_agent=user_agent,
        )
        await self.session_repo.create(session)
        return create_session_token(session_id)
