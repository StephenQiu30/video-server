from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query

from app.api.auth_dependencies import get_current_admin, get_user_service
from app.api.errors import auth_application_error
from app.api.schemas.users import (
    ManagedUserListResponse,
    ManagedUserResponse,
    UpdateUserAccessRequest,
)
from app.application.auth import AuthError, CurrentUser, UserRole, UserService

router = APIRouter(prefix="/admin/users", tags=["admin"])
Admin = Annotated[CurrentUser, Depends(get_current_admin)]
Users = Annotated[UserService, Depends(get_user_service)]


@router.get(
    "",
    operation_id="listUsers",
    response_model=ManagedUserListResponse,
    summary="查询用户列表",
)
async def list_users(
    admin: Admin,
    users: Users,
    page: Annotated[int, Query(ge=1, le=10_000)] = 1,
    page_size: Annotated[int, Query(ge=1, le=50)] = 20,
    search: Annotated[str | None, Query(max_length=128)] = None,
    role: UserRole | None = None,
    is_active: bool | None = None,
) -> ManagedUserListResponse:
    try:
        result = await users.list_users(
            admin,
            page=page,
            page_size=page_size,
            search=search,
            role=role,
            is_active=is_active,
        )
    except AuthError as exc:
        raise auth_application_error(exc) from exc
    return ManagedUserListResponse.from_page(result)


@router.patch(
    "/{user_id}",
    operation_id="updateUserAccess",
    response_model=ManagedUserResponse,
    summary="更新用户角色与账号状态",
)
async def update_user_access(
    user_id: UUID,
    body: UpdateUserAccessRequest,
    admin: Admin,
    users: Users,
) -> ManagedUserResponse:
    try:
        updated = await users.update_access(
            admin,
            user_id,
            role=body.role,
            is_active=body.is_active,
        )
    except AuthError as exc:
        raise auth_application_error(exc) from exc
    return ManagedUserResponse.from_user(updated)
