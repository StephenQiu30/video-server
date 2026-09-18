from typing import Annotated

from fastapi import APIRouter, Depends

from app.api.deps import get_current_user, get_user_service
from app.api.errors import auth_application_error
from app.schemas.auth import UserResponse
from app.schemas.users import UpdateProfileRequest
from app.services.auth.errors import AuthError
from app.services.auth.models import CurrentUser
from app.services.auth.user_service import UserService

router = APIRouter(prefix="/users", tags=["users"])
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
    try:
        updated = await users.update_profile(user, body.username)
    except AuthError as exc:
        raise auth_application_error(exc) from exc
    return UserResponse.from_user(updated)
