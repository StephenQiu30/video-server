from __future__ import annotations

import hashlib
from typing import Annotated

from fastapi import APIRouter, Depends, Header, Request, Response, status

from app.api.admission import enforce_rate_limit
from app.api.deps import (
    clear_auth_cookies,
    get_auth_service,
    get_runtime_settings,
    get_web_session_service,
    get_web_user,
    set_auth_cookies,
)
from app.api.operation_logging import identify_operation_actor
from app.api.responses import ApiResponseRoute
from app.core.config import Settings
from app.schemas.auth import (
    EmailPasswordRequest,
    RegisterRequest,
    RegistrationCodeRequest,
    RegistrationCodeResponse,
    RegistrationCodeVerificationRequest,
    RegistrationCodeVerificationResponse,
    UserResponse,
)
from app.services.auth.models import CurrentUser
from app.services.auth.service import AuthService
from app.services.auth.web_sessions import WebSessionService

router = APIRouter(route_class=ApiResponseRoute, prefix="/auth", tags=["auth"])
Auth = Annotated[AuthService, Depends(get_auth_service)]
WebSessions = Annotated[WebSessionService, Depends(get_web_session_service)]
SettingsDependency = Annotated[Settings, Depends(get_runtime_settings)]
User = Annotated[CurrentUser, Depends(get_web_user)]


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
    "/registration-code/verify",
    operation_id="verifyRegistrationCode",
    response_model=RegistrationCodeVerificationResponse,
    summary="验证注册邮箱验证码",
)
async def verify_registration_code(
    body: RegistrationCodeVerificationRequest,
    request: Request,
    auth: Auth,
    settings: SettingsDependency,
) -> RegistrationCodeVerificationResponse:
    await enforce_rate_limit(
        request,
        "registration_code_verify",
        _email_hash(str(body.email)),
        settings,
        include_client_ip=True,
    )
    await auth.verify_registration_code(str(body.email), body.verification_code)
    return RegistrationCodeVerificationResponse()


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
    web: WebSessions,
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
    user = await auth.register_account(
        body.username,
        str(body.email),
        body.password,
        bootstrap_secret=bootstrap_secret,
        verification_code=body.verification_code,
    )
    grant = await web.issue(
        user.id, previous_token=request.cookies.get(settings.auth_web_cookie_name)
    )
    set_auth_cookies(response, settings, grant)
    response.headers["Location"] = "/api/auth/me"
    identify_operation_actor(grant.user)
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
    web: WebSessions,
    settings: SettingsDependency,
) -> UserResponse:
    await enforce_rate_limit(
        request,
        "login",
        _email_hash(str(body.email)),
        settings,
        include_client_ip=True,
    )
    user = await auth.authenticate(str(body.email), body.password)
    grant = await web.issue(
        user.id, previous_token=request.cookies.get(settings.auth_web_cookie_name)
    )
    set_auth_cookies(response, settings, grant)
    identify_operation_actor(grant.user)
    return UserResponse.from_user(grant.user)


@router.get(
    "/me",
    operation_id="getCurrentUser",
    response_model=UserResponse,
    summary="查询当前用户",
)
async def get_current_user_profile(user: User, response: Response) -> UserResponse:
    response.headers["Cache-Control"] = "no-store"
    return UserResponse.from_user(user)


@router.post(
    "/logout",
    operation_id="logoutUser",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="退出登录",
)
async def logout_user(
    request: Request,
    response: Response,
    web: WebSessions,
    settings: SettingsDependency,
) -> None:
    user_id = await web.revoke(request.cookies.get(settings.auth_web_cookie_name, ""))
    clear_auth_cookies(response, settings)
    hub = getattr(request.app.state.services, "realtime_hub", None)
    if user_id is not None and hub is not None:
        hub.invalidate_owner(hashlib.sha256(str(user_id).encode()).hexdigest())


def _email_hash(email: str) -> str:
    return hashlib.sha256(email.strip().casefold().encode()).hexdigest()
