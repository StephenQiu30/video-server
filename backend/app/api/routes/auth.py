from __future__ import annotations

import hashlib
from typing import Annotated

from fastapi import APIRouter, Depends, Header, Request, Response, status

from app.api.admission import enforce_rate_limit
from app.api.deps import (
    clear_auth_cookies,
    get_auth_service,
    get_current_user,
    get_runtime_settings,
    set_auth_cookies,
)
from app.api.errors import app_error_handler, auth_application_error
from app.api.responses import ApiResponseRoute
from app.core.config import Settings
from app.schemas.auth import (
    EmailPasswordRequest,
    RegisterRequest,
    RegistrationCodeRequest,
    RegistrationCodeResponse,
    UserResponse,
)
from app.services.auth.errors import AuthError, AuthErrorCode
from app.services.auth.models import CurrentUser
from app.services.auth.service import AuthService

router = APIRouter(route_class=ApiResponseRoute, prefix="/auth", tags=["auth"])
Auth = Annotated[AuthService, Depends(get_auth_service)]
SettingsDependency = Annotated[Settings, Depends(get_runtime_settings)]
User = Annotated[CurrentUser, Depends(get_current_user)]


@router.post(
    "/registration-code",
    operation_id="sendRegistrationCode",
    response_model=RegistrationCodeResponse,
    summary="发送注册邮箱验证码",
)
async def send_registration_code(
    body: RegistrationCodeRequest,
    request: Request,
    auth: Auth,
    settings: SettingsDependency,
) -> RegistrationCodeResponse:
    await enforce_rate_limit(
        request,
        "registration_code",
        _email_hash(str(body.email)),
        settings,
        include_client_ip=True,
    )
    await auth.send_registration_code(str(body.email))
    return RegistrationCodeResponse()


@router.post(
    "/register",
    operation_id="registerUser",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
    summary="使用邮箱注册",
)
async def register_user(
    body: RegisterRequest,
    request: Request,
    response: Response,
    auth: Auth,
    settings: SettingsDependency,
    bootstrap_secret: Annotated[
        str | None, Header(alias="X-Admin-Bootstrap-Secret")
    ] = None,
) -> UserResponse:
    await enforce_rate_limit(
        request,
        "register",
        _email_hash(str(body.email)),
        settings,
        include_client_ip=True,
    )
    grant = await auth.register(
        body.username,
        str(body.email),
        body.password,
        bootstrap_secret=bootstrap_secret,
        verification_code=body.verification_code,
    )
    set_auth_cookies(response, settings, grant)
    response.headers["Location"] = "/api/auth/me"
    return UserResponse.from_user(grant.user)


@router.post(
    "/login",
    operation_id="loginUser",
    response_model=UserResponse,
    summary="使用邮箱登录",
)
async def login_user(
    body: EmailPasswordRequest,
    request: Request,
    response: Response,
    auth: Auth,
    settings: SettingsDependency,
) -> UserResponse:
    await enforce_rate_limit(
        request,
        "login",
        _email_hash(str(body.email)),
        settings,
        include_client_ip=True,
    )
    grant = await auth.login(str(body.email), body.password)
    set_auth_cookies(response, settings, grant)
    return UserResponse.from_user(grant.user)


@router.get(
    "/me",
    operation_id="getCurrentUser",
    response_model=UserResponse,
    summary="查询当前用户",
)
async def get_current_user_profile(user: User) -> UserResponse:
    return UserResponse.from_user(user)


@router.post(
    "/refresh",
    operation_id="refreshUserSession",
    response_model=UserResponse,
    summary="刷新登录会话",
)
async def refresh_user_session(
    request: Request,
    response: Response,
    auth: Auth,
    settings: SettingsDependency,
) -> UserResponse | Response:
    refresh_token = request.cookies.get(settings.auth_refresh_cookie_name)
    if not refresh_token:
        return await _cleared_auth_error_response(
            request, settings, AuthError(AuthErrorCode.UNAUTHENTICATED)
        )
    try:
        grant = await auth.refresh(refresh_token)
    except AuthError as exc:
        return await _cleared_auth_error_response(request, settings, exc)
    set_auth_cookies(response, settings, grant)
    return UserResponse.from_user(grant.user)


@router.post(
    "/logout",
    operation_id="logoutUser",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="退出登录",
)
async def logout_user(
    request: Request,
    response: Response,
    auth: Auth,
    settings: SettingsDependency,
) -> None:
    access_token = request.cookies.get(settings.auth_access_cookie_name)
    try:
        user = await auth.current_user(access_token or "")
    except AuthError:
        user = None
    refresh_token = request.cookies.get(settings.auth_refresh_cookie_name)
    if refresh_token:
        await auth.logout(refresh_token)
    clear_auth_cookies(response, settings)
    hub = getattr(request.app.state.services, "realtime_hub", None)
    if user is not None and hub is not None:
        hub.invalidate_owner(user.owner_hash)


def _email_hash(email: str) -> str:
    return hashlib.sha256(email.strip().casefold().encode()).hexdigest()


async def _cleared_auth_error_response(
    request: Request, settings: Settings, error: AuthError
) -> Response:
    response = await app_error_handler(request, auth_application_error(error))
    clear_auth_cookies(response, settings)
    return response
