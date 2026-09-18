from __future__ import annotations

import hashlib
from typing import Annotated

from fastapi import APIRouter, Depends, Request, Response, status

from app.api.admission import enforce_rate_limit
from app.api.deps import get_auth_service, get_current_user, get_runtime_settings
from app.api.openapi import ERROR_RESPONSES as WEB_ERROR_RESPONSES
from app.core.config import Settings
from app.schemas.auth import (
    EmailPasswordRequest,
    RegisterRequest,
    RegistrationCodeRequest,
    RegistrationCodeResponse,
    UserResponse,
)
from app.schemas.errors import ProblemDetails
from app.schemas.native_auth import (
    NativeLogoutRequest,
    NativeRefreshRequest,
    NativeSessionResponse,
)
from app.services.auth.models import CurrentUser
from app.services.auth.service import AuthService

ERROR_RESPONSES = {
    status: {**spec, "model": ProblemDetails}
    for status, spec in WEB_ERROR_RESPONSES.items()
}

router = APIRouter(
    prefix="/api/app/v1/auth",
    tags=["app-auth"],
    responses=ERROR_RESPONSES,
)
Auth = Annotated[AuthService, Depends(get_auth_service)]
SettingsDependency = Annotated[Settings, Depends(get_runtime_settings)]
User = Annotated[CurrentUser, Depends(get_current_user)]


@router.post(
    "/registration-code",
    operation_id="sendNativeRegistrationCode",
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
        request, "registration_code", _email_hash(str(body.email)), settings
    )
    await auth.send_registration_code(str(body.email))
    return RegistrationCodeResponse()


@router.post(
    "/register",
    operation_id="registerNativeUser",
    response_model=NativeSessionResponse,
    status_code=status.HTTP_201_CREATED,
    summary="注册原生应用用户",
)
async def register_native_user(
    body: RegisterRequest,
    request: Request,
    response: Response,
    auth: Auth,
    settings: SettingsDependency,
) -> NativeSessionResponse:
    await enforce_rate_limit(
        request, "register", _email_hash(str(body.email)), settings
    )
    grant = await auth.register(
        body.username,
        str(body.email),
        body.password,
        verification_code=body.verification_code,
    )
    response.headers["Location"] = "/api/app/v1/auth/me"
    return NativeSessionResponse.from_grant(grant)


@router.post(
    "/login",
    operation_id="loginNativeUser",
    response_model=NativeSessionResponse,
    summary="登录原生应用",
)
async def login_native_user(
    body: EmailPasswordRequest,
    request: Request,
    auth: Auth,
    settings: SettingsDependency,
) -> NativeSessionResponse:
    await enforce_rate_limit(request, "login", _email_hash(str(body.email)), settings)
    grant = await auth.login(str(body.email), body.password)
    return NativeSessionResponse.from_grant(grant)


@router.get(
    "/me",
    operation_id="getNativeCurrentUser",
    response_model=UserResponse,
    summary="查询原生应用当前用户",
)
async def get_native_current_user(user: User) -> UserResponse:
    return UserResponse.from_user(user)


@router.post(
    "/refresh",
    operation_id="refreshNativeSession",
    response_model=NativeSessionResponse,
    summary="轮换原生应用会话",
)
async def refresh_native_session(
    body: NativeRefreshRequest,
    auth: Auth,
) -> NativeSessionResponse:
    grant = await auth.refresh(body.refresh_token)
    return NativeSessionResponse.from_grant(grant)


@router.post(
    "/logout",
    operation_id="logoutNativeSession",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="退出原生应用",
)
async def logout_native_session(body: NativeLogoutRequest, auth: Auth) -> None:
    await auth.logout(body.refresh_token)


def _email_hash(email: str) -> str:
    return hashlib.sha256(email.strip().casefold().encode()).hexdigest()
