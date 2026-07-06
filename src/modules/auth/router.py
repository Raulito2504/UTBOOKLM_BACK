from fastapi import APIRouter, status
from sqlalchemy.exc import IntegrityError

from src.api.v1.dependencies import CurrentUser, DatabaseSession
from src.core.config import get_settings
from src.core.exceptions import AppError
from src.modules.auth import service
from src.modules.auth.schemas import (
    AccessTokenResponse,
    LoginRequest,
    MessageResponse,
    PasswordForgotRequest,
    PasswordForgotResponse,
    PasswordResetRequest,
    RefreshTokenRequest,
    RegisterRequest,
    TokenResponse,
    UserResponse,
)


router = APIRouter()


@router.get("/health")
async def health() -> dict[str, str]:
    return {"module": "auth", "status": "ready"}


@router.post(
    "/register",
    response_model=TokenResponse,
    status_code=status.HTTP_201_CREATED,
)
async def register(payload: RegisterRequest, db: DatabaseSession) -> TokenResponse:
    try:
        user = await service.register_user(
            db,
            email=payload.email,
            password=payload.password,
            name=payload.name,
            organization_name=payload.organization_name,
        )
        refresh_token = await service.create_user_refresh_token(db, user=user)
        await db.commit()
        await db.refresh(user)
    except service.EmailAlreadyRegisteredError:
        await db.rollback()
        raise AppError(
            status_code=status.HTTP_409_CONFLICT,
            error_code="email_already_registered",
            message="Email already registered",
        ) from None
    except IntegrityError:
        await db.rollback()
        raise AppError(
            status_code=status.HTTP_409_CONFLICT,
            error_code="resource_conflict",
            message="Could not create account with the provided data",
        ) from None

    return TokenResponse(
        access_token=service.create_user_access_token(user),
        refresh_token=refresh_token,
        user=UserResponse.model_validate(user),
    )


@router.post("/login", response_model=TokenResponse)
async def login(payload: LoginRequest, db: DatabaseSession) -> TokenResponse:
    user = await service.authenticate_user(
        db,
        email=payload.email,
        password=payload.password,
    )
    if user is None:
        raise AppError(
            status_code=status.HTTP_401_UNAUTHORIZED,
            error_code="invalid_credentials",
            message="Invalid credentials",
        )

    refresh_token = await service.create_user_refresh_token(db, user=user)
    await db.commit()

    return TokenResponse(
        access_token=service.create_user_access_token(user),
        refresh_token=refresh_token,
        user=UserResponse.model_validate(user),
    )


@router.post("/refresh", response_model=AccessTokenResponse)
async def refresh(payload: RefreshTokenRequest, db: DatabaseSession) -> AccessTokenResponse:
    try:
        access_token = await service.refresh_access_token(
            db,
            refresh_token=payload.refresh_token,
        )
    except service.RefreshTokenExpiredError:
        raise AppError(
            status_code=status.HTTP_401_UNAUTHORIZED,
            error_code="refresh_token_expired",
            message="Refresh token expired",
        ) from None
    except service.RefreshTokenRevokedError:
        raise AppError(
            status_code=status.HTTP_401_UNAUTHORIZED,
            error_code="refresh_token_revoked",
            message="Refresh token revoked",
        ) from None
    except service.RefreshTokenInvalidError:
        raise AppError(
            status_code=status.HTTP_401_UNAUTHORIZED,
            error_code="refresh_token_invalid",
            message="Refresh token invalid",
        ) from None

    return AccessTokenResponse(access_token=access_token)


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout(payload: RefreshTokenRequest, db: DatabaseSession) -> None:
    try:
        await service.revoke_user_refresh_token(
            db,
            refresh_token=payload.refresh_token,
        )
        await db.commit()
    except service.RefreshTokenExpiredError:
        await db.rollback()
        raise AppError(
            status_code=status.HTTP_401_UNAUTHORIZED,
            error_code="refresh_token_expired",
            message="Refresh token expired",
        ) from None
    except service.RefreshTokenRevokedError:
        await db.rollback()
        raise AppError(
            status_code=status.HTTP_401_UNAUTHORIZED,
            error_code="refresh_token_revoked",
            message="Refresh token revoked",
        ) from None
    except service.RefreshTokenInvalidError:
        await db.rollback()
        raise AppError(
            status_code=status.HTTP_401_UNAUTHORIZED,
            error_code="refresh_token_invalid",
            message="Refresh token invalid",
        ) from None


@router.post("/password/forgot", response_model=PasswordForgotResponse)
async def forgot_password(
    payload: PasswordForgotRequest,
    db: DatabaseSession,
) -> PasswordForgotResponse:
    reset_token = await service.request_password_reset(db, email=payload.email)
    await db.commit()
    settings = get_settings()
    return PasswordForgotResponse(
        message="If the email exists, password reset instructions were sent",
        reset_token=None if settings.is_production else reset_token,
    )


@router.post("/password/reset", response_model=MessageResponse)
async def reset_password(
    payload: PasswordResetRequest,
    db: DatabaseSession,
) -> MessageResponse:
    try:
        await service.reset_password(
            db,
            reset_token=payload.reset_token,
            new_password=payload.new_password,
        )
        await db.commit()
    except service.PasswordResetTokenExpiredError:
        await db.rollback()
        raise AppError(
            status_code=status.HTTP_401_UNAUTHORIZED,
            error_code="password_reset_token_expired",
            message="Password reset token expired",
        ) from None
    except service.PasswordResetTokenUsedError:
        await db.rollback()
        raise AppError(
            status_code=status.HTTP_401_UNAUTHORIZED,
            error_code="password_reset_token_used",
            message="Password reset token already used",
        ) from None
    except service.PasswordResetTokenInvalidError:
        await db.rollback()
        raise AppError(
            status_code=status.HTTP_401_UNAUTHORIZED,
            error_code="password_reset_token_invalid",
            message="Password reset token invalid",
        ) from None

    return MessageResponse(message="Password reset successfully")


@router.get("/me", response_model=UserResponse)
async def me(current_user: CurrentUser) -> UserResponse:
    return UserResponse.model_validate(current_user)
