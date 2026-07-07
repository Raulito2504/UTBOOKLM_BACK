from fastapi import APIRouter, Cookie, status
from fastapi.responses import RedirectResponse
from sqlalchemy.exc import IntegrityError

from src.api.v1.dependencies import CurrentUser, DatabaseSession
from src.core.config import get_settings
from src.core.exceptions import AppError
from src.modules.auth import google_oauth, service
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
GOOGLE_OAUTH_STATE_COOKIE = "utbooklm_google_oauth_state"


@router.get("/health")
async def health() -> dict[str, str]:
    return {"module": "auth", "status": "ready"}


@router.get("/google/login")
async def google_login() -> RedirectResponse:
    settings = get_settings()
    try:
        authorization_url, state_token = google_oauth.create_google_authorization_url(
            settings,
        )
    except google_oauth.GoogleAuthDisabledError:
        raise AppError(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            error_code="google_auth_disabled",
            message="Google authentication is disabled",
        ) from None
    except google_oauth.GoogleAuthConfigMissingError:
        raise AppError(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            error_code="google_auth_config_missing",
            message="Google authentication is not configured",
        ) from None

    response = RedirectResponse(authorization_url)
    response.set_cookie(
        GOOGLE_OAUTH_STATE_COOKIE,
        state_token,
        max_age=600,
        httponly=True,
        secure=settings.is_production,
        samesite="lax",
    )
    return response


@router.get("/google/callback")
async def google_callback(
    db: DatabaseSession,
    code: str | None = None,
    state: str | None = None,
    stored_state: str | None = Cookie(
        None,
        alias=GOOGLE_OAUTH_STATE_COOKIE,
    ),
) -> RedirectResponse:
    if not code:
        raise AppError(
            status_code=status.HTTP_400_BAD_REQUEST,
            error_code="google_auth_code_invalid",
            message="Invalid Google authentication code",
        )
    if not state or not stored_state or state != stored_state:
        raise AppError(
            status_code=status.HTTP_400_BAD_REQUEST,
            error_code="google_auth_state_invalid",
            message="Invalid Google authentication state",
        )

    settings = get_settings()
    try:
        profile = await google_oauth.fetch_google_profile(settings, code=code)
        login_result = await google_oauth.login_or_create_google_user(
            db,
            profile=profile,
        )
        await db.commit()
        await db.refresh(login_result.user)
    except google_oauth.GoogleAuthDisabledError:
        await db.rollback()
        raise AppError(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            error_code="google_auth_disabled",
            message="Google authentication is disabled",
        ) from None
    except google_oauth.GoogleAuthConfigMissingError:
        await db.rollback()
        raise AppError(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            error_code="google_auth_config_missing",
            message="Google authentication is not configured",
        ) from None
    except google_oauth.GoogleAuthCodeInvalidError:
        await db.rollback()
        raise AppError(
            status_code=status.HTTP_400_BAD_REQUEST,
            error_code="google_auth_code_invalid",
            message="Invalid Google authentication code",
        ) from None
    except google_oauth.GoogleProfileInvalidError:
        await db.rollback()
        raise AppError(
            status_code=status.HTTP_400_BAD_REQUEST,
            error_code="google_profile_invalid",
            message="Google profile is invalid",
        ) from None
    except google_oauth.GoogleEmailNotVerifiedError:
        await db.rollback()
        raise AppError(
            status_code=status.HTTP_401_UNAUTHORIZED,
            error_code="google_email_not_verified",
            message="Google email is not verified",
        ) from None
    except google_oauth.GoogleUserInactiveError:
        await db.rollback()
        raise AppError(
            status_code=status.HTTP_403_FORBIDDEN,
            error_code="google_user_inactive",
            message="Google user is inactive",
        ) from None
    except IntegrityError:
        await db.rollback()
        raise AppError(
            status_code=status.HTTP_409_CONFLICT,
            error_code="resource_conflict",
            message="Could not create account with the provided Google profile",
        ) from None

    redirect_url = google_oauth.build_frontend_auth_redirect_url(
        settings,
        access_token=login_result.access_token,
        refresh_token=login_result.refresh_token,
    )
    response = RedirectResponse(redirect_url)
    response.delete_cookie(GOOGLE_OAUTH_STATE_COOKIE)
    return response


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
