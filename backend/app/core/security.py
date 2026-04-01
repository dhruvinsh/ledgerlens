import bcrypt
from itsdangerous import URLSafeTimedSerializer

from app.core.config import settings

_serializer = URLSafeTimedSerializer(settings.SECRET_KEY)


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()


def verify_password(password: str, password_hash: str) -> bool:
    return bcrypt.checkpw(password.encode(), password_hash.encode())


def create_session_token(session_id: str) -> str:
    return _serializer.dumps(session_id, salt="session")


def verify_session_token(token: str, max_age: int = 30 * 24 * 3600) -> str | None:
    try:
        return _serializer.loads(token, salt="session", max_age=max_age)  # type: ignore[no-any-return]
    except Exception:
        return None


def create_invite_token(household_id: str) -> str:
    return _serializer.dumps({"household_id": household_id}, salt="household-invite")


def verify_invite_token(token: str, max_age: int = 7 * 24 * 3600) -> dict[str, str] | None:
    try:
        return _serializer.loads(token, salt="household-invite", max_age=max_age)  # type: ignore[no-any-return]
    except Exception:
        return None
