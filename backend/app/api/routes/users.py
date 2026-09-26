from typing import Annotated

from fastapi import APIRouter, Body, Depends, Response

from app.api.admission import RateLimitAdmission
from app.api.deps import get_current_user, get_user_service
from app.api.responses import ApiResponseRoute
from app.core.errors import AppError
from app.schemas.auth import UserResponse
from app.schemas.users import UpdateProfileRequest
from app.services.auth.avatars import InvalidAvatar
from app.services.auth.models import CurrentUser
from app.services.auth.user_service import UserService

router = APIRouter(route_class=ApiResponseRoute, prefix="/users", tags=["users"])
User = Annotated[CurrentUser, Depends(get_current_user)]
Users = Annotated[UserService, Depends(get_user_service)]


@router.patch(
    "/me",
    operation_id="updateCurrentUser",
    response_model=UserResponse,
    summary="更新当前用户资料",
)
async def update_current_user(
    body: UpdateProfileRequest,
    user: User,
    users: Users,
) -> UserResponse:
    updated = await users.update_profile(user, body.username)
    return UserResponse.from_user(updated)


@router.put(
    "/me/avatar",
    operation_id="uploadCurrentUserAvatar",
    dependencies=[Depends(RateLimitAdmission("avatar_upload"))],
    openapi_extra={
        "requestBody": {
            "content": {
                "application/octet-stream": {
                    "schema": {"type": "string", "format": "binary"}
                }
            }
        }
    },
    response_model=UserResponse,
    summary="上传当前用户头像",
)
async def upload_current_user_avatar(
    body: Annotated[bytes, Body(media_type="application/octet-stream")],
    user: User,
    users: Users,
) -> UserResponse:
    try:
        updated = await users.set_avatar(user, body)
    except InvalidAvatar as exc:
        raise AppError(
            status=422,
            code="invalid_request",
            title="Invalid avatar",
            detail=str(exc),
        ) from exc
    return UserResponse.from_user(updated)


@router.get(
    "/me/avatar",
    operation_id="getCurrentUserAvatar",
    responses={
        200: {
            "content": {
                "image/webp": {"schema": {"type": "string", "format": "binary"}}
            }
        }
    },
    summary="读取当前用户头像",
)
async def get_current_user_avatar(user: User, users: Users) -> Response:
    avatar = await users.get_avatar(user)
    if avatar is None:
        raise AppError(
            status=404,
            code="not_found",
            title="Avatar not found",
            detail="The current user has no avatar.",
        )
    return Response(
        content=avatar,
        media_type="image/webp",
        headers={"Cache-Control": "private, no-store"},
    )


@router.delete(
    "/me/avatar",
    operation_id="deleteCurrentUserAvatar",
    response_model=UserResponse,
    summary="移除当前用户头像",
)
async def delete_current_user_avatar(user: User, users: Users) -> UserResponse:
    updated = await users.delete_avatar(user)
    return UserResponse.from_user(updated)
