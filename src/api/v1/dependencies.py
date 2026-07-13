from collections.abc import Callable
from typing import Annotated
import uuid
# Ya quedo
from fastapi import Depends, Query, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.config import get_settings
from src.core.database import get_db
from src.core.exceptions import AppError
from src.core.security import TokenExpiredError, TokenInvalidError, decode_token
from src.models import User, UserRole
from src.modules.auth import repository as auth_repository


DatabaseSession = Annotated[AsyncSession, Depends(get_db)]
bearer_scheme = HTTPBearer(auto_error=False)


async def get_current_user(
    db: DatabaseSession,
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer_scheme)],
) -> User:
    settings = get_settings()
    if not settings.auth_enabled:
        raise AppError(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            error_code="auth_disabled",
            message="Authentication is disabled in this environment",
        )

    if credentials is None:
        raise AppError(
            status_code=status.HTTP_401_UNAUTHORIZED,
            error_code="missing_credentials",
            message="Missing authorization credentials",
        )

    try:
        payload = decode_token(credentials.credentials)
        user_id = uuid.UUID(str(payload["sub"]))
    except TokenExpiredError:
        raise AppError(
            status_code=status.HTTP_401_UNAUTHORIZED,
            error_code="token_expired",
            message="Authorization token expired",
        ) from None
    except (KeyError, TypeError, TokenInvalidError, ValueError):
        raise AppError(
            status_code=status.HTTP_401_UNAUTHORIZED,
            error_code="token_invalid",
            message="Invalid authorization token",
        ) from None

    user = await auth_repository.get_user_by_id(db, user_id=user_id)
    if user is None or not user.is_active:
        raise AppError(
            status_code=status.HTTP_401_UNAUTHORIZED,
            error_code="invalid_credentials",
            message="Invalid credentials",
        )
    return user


CurrentUser = Annotated[User, Depends(get_current_user)]


def require_roles(*allowed_roles: UserRole) -> Callable[[CurrentUser], User]:
    async def role_dependency(current_user: CurrentUser) -> User:
        if current_user.role not in allowed_roles:
            raise AppError(
                status_code=status.HTTP_403_FORBIDDEN,
                error_code="permission_denied",
                message="You do not have permission to access this resource",
            )
        return current_user

    return role_dependency


AdminUser = Annotated[User, Depends(require_roles(UserRole.ADMIN))]
TeacherUser = Annotated[
    User,
    Depends(require_roles(UserRole.ADMIN, UserRole.TEACHER)),
]


def pagination_params(
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> dict[str, int]:
    return {"limit": limit, "offset": offset}
