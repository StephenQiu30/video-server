from __future__ import annotations

import hashlib
from typing import Annotated

from fastapi import APIRouter, Depends, Request, Response, status

from app.api.auth_dependencies import (
    enforce_rate_limit,
    get_auth_service,
    get_current_user,
)
from app.api.dependencies import get_runtime_settings
from app.api.errors import auth_application_error
from app.api.openapi import ERROR_RESPONSES
from app.api.schemas.auth import EmailPasswordRequest, RegisterRequest, UserResponse
from app.api.schemas.native_auth import (
    NativeLogoutRequest,
    NativeRefreshRequest,
    NativeSessionResponse,
)
from app.application.auth import AuthError, AuthService, CurrentUser
from app.core.config import Settings

router = APIRouter(
    prefix="/api/app/v1/auth",
    tags=["app-auth"],
    responses=ERROR_RESPONSES,
)
Auth = Annotated[AuthService, Depends(get_auth_service)]
SettingsDependency = Annotated[Settings, Depends(get_runtime_settings)]
User = Annotated[CurrentUser, Depends(get_current_user)]


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
    try:
        grant = await auth.register(body.username, str(body.email), body.password)
    except AuthError as exc:
        raise auth_application_error(exc) from exc
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
    try:
        grant = await auth.login(str(body.email), body.password)
    except AuthError as exc:
        raise auth_application_error(exc) from exc
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
    try:
        grant = await auth.refresh(body.refresh_token)
    except AuthError as exc:
        raise auth_application_error(exc) from exc
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
