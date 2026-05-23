import httpx
import logging
import json
from datetime import timedelta
from functools import lru_cache
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import RedirectResponse
from redis import Redis
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.errors import AppError
from app.core.security import create_access_token, hash_password, verify_password
from app.db.session import get_db
from app.deps import get_current_user
from app.models import User
from app.schemas import Token, UserCreate, UserLogin, UserRead
from app.services.auth_lock import InMemoryAuthLock, RedisAuthLock

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/auth", tags=["auth"])


@lru_cache
def get_auth_lock():
    settings = get_settings()
    if settings.app_env not in {"local", "testing"}:
        return RedisAuthLock(
            Redis.from_url(settings.redis_url),
            max_failures=settings.auth_login_failure_limit,
            lock_seconds=settings.auth_lock_seconds,
            register_limit=settings.auth_register_rate_limit_per_hour,
        )
    return InMemoryAuthLock(
        max_failures=settings.auth_login_failure_limit,
        lock_seconds=settings.auth_lock_seconds,
        register_limit=settings.auth_register_rate_limit_per_hour,
    )


@router.get("/github/authorize")
def github_authorize() -> RedirectResponse:
    settings = get_settings()
    if not settings.github_client_id:
        raise HTTPException(status_code=500, detail="GitHub OAuth not configured")
    
    url = (
        "https://github.com/login/oauth/authorize"
        f"?client_id={settings.github_client_id}"
        "&scope=user:email"
    )
    return RedirectResponse(url)


@router.post("/register", response_model=Token, status_code=201)
def register_user(
    payload: UserCreate,
    request: Request,
    db: Annotated[Session, Depends(get_db)],
) -> dict:
    settings = get_settings()
    if not settings.registration_enabled:
        raise AppError("registration_disabled", "注册暂未开放", 403)
    if settings.registration_invite_code and payload.invite_code != settings.registration_invite_code:
        raise AppError("registration_failed", "注册失败，请检查输入或稍后重试", 400)

    client_ip = _client_ip(request)
    get_auth_lock().assert_register_allowed(client_ip)
    normalized_email = payload.email.strip().lower()
    existing = db.scalar(select(User).where(User.email == normalized_email))
    if existing:
        raise AppError("registration_failed", "注册失败，请检查输入或稍后重试", 400)

    user = User(
        email=normalized_email,
        password_hash=hash_password(payload.password),
        display_name=payload.display_name,
        daily_task_quota=settings.default_daily_task_quota,
        storage_quota_bytes=settings.default_storage_quota_bytes,
        concurrent_task_quota=settings.per_user_download_concurrency,
        max_file_size_bytes=settings.max_file_size_bytes,
        file_retention_hours=settings.file_retention_hours,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return _token_for_user(user)


@router.post("/login", response_model=Token)
def login_user(
    request: Request,
    payload: UserLogin,
    db: Annotated[Session, Depends(get_db)],
) -> dict:
    email = payload.email.strip().lower()
    client_ip = _client_ip(request)
    auth_lock = get_auth_lock()
    auth_lock.assert_login_allowed(email, client_ip)
    user = db.scalar(select(User).where(User.email == email))
    if not user or not user.password_hash or not verify_password(payload.password, user.password_hash):
        auth_lock.record_login_failure(email, client_ip)
        raise AppError("invalid_credentials", "邮箱或密码错误", 401)
    if not user.is_active:
        raise AppError("user_disabled", "账号不可用", 403)
    auth_lock.clear_login(email)
    return _token_for_user(user)


@router.get(
    "/github/callback",
    status_code=status.HTTP_307_TEMPORARY_REDIRECT,
    response_class=RedirectResponse,
    responses={
        status.HTTP_307_TEMPORARY_REDIRECT: {
            "description": "GitHub OAuth 登录成功后重定向到前端，并携带一次性前端处理的 token 查询参数。",
        }
    },
)
async def github_callback(
    code: str,
    db: Annotated[Session, Depends(get_db)],
) -> RedirectResponse:
    settings = get_settings()
    if not settings.github_client_id or not settings.github_client_secret:
        raise HTTPException(status_code=500, detail="GitHub OAuth not configured")

    async with httpx.AsyncClient() as client:
        # 1. Exchange code for access token
        token_res = await client.post(
            "https://github.com/login/oauth/access_token",
            params={
                "client_id": settings.github_client_id,
                "client_secret": settings.github_client_secret,
                "code": code,
            },
            headers={
                "Accept": "application/json",
                "User-Agent": "StephenVideo-API"
            },
        )
        token_res.raise_for_status()
        token_data = token_res.json()
        gh_access_token = token_data.get("access_token")
        if not gh_access_token:
            logger.error(f"GitHub token exchange failed: {token_data}")
            raise HTTPException(status_code=400, detail="Failed to get GitHub access token")

        # 2. Get user info
        user_res = await client.get(
            "https://api.github.com/user",
            headers={
                "Authorization": f"token {gh_access_token}",
                "Accept": "application/json",
                "User-Agent": "StephenVideo-API"
            },
        )
        try:
            user_res.raise_for_status()
            gh_user = user_res.json()
        except (httpx.HTTPStatusError, json.JSONDecodeError) as e:
            logger.error(f"Failed to fetch GitHub user profile: {str(e)}")
            logger.error(f"GitHub Response: {user_res.text[:500]}")
            raise HTTPException(status_code=400, detail="Failed to retrieve user info from GitHub")
            
        gh_id = str(gh_user.get("id"))
        
        # 3. Get primary email if not public
        email = gh_user.get("email")
        if not email:
            emails_res = await client.get(
                "https://api.github.com/user/emails",
                headers={
                    "Authorization": f"token {gh_access_token}",
                    "Accept": "application/json",
                    "User-Agent": "StephenVideo-API"
                },
            )
            try:
                emails_res.raise_for_status()
                emails = emails_res.json()
                primary_email = next((e["email"] for e in emails if e["primary"]), emails[0]["email"])
                email = primary_email
            except (httpx.HTTPStatusError, json.JSONDecodeError, IndexError) as e:
                logger.error(f"Failed to fetch GitHub user emails: {str(e)}")
                raise HTTPException(status_code=400, detail="Failed to retrieve email from GitHub")

    # 4. Quiet registration / Login
    user = db.scalar(select(User).where(User.github_id == gh_id))
    if not user:
        # Check if user with same email exists
        user = db.scalar(select(User).where(User.email == email))
        if user:
            # Bind existing user to GitHub
            user.github_id = gh_id
            user.avatar_url = gh_user.get("avatar_url")
        else:
            # Create new user
            user = User(
                email=email,
                github_id=gh_id,
                avatar_url=gh_user.get("avatar_url"),
                display_name=gh_user.get("name") or gh_user.get("login"),
                daily_task_quota=settings.default_daily_task_quota,
                storage_quota_bytes=settings.default_storage_quota_bytes,
                concurrent_task_quota=settings.per_user_download_concurrency,
                max_file_size_bytes=settings.max_file_size_bytes,
                file_retention_hours=settings.file_retention_hours,
            )
            db.add(user)
        db.commit()
        db.refresh(user)

    # 5. Issue our own JWT
    access_token_expires = timedelta(minutes=settings.access_token_expire_minutes)
    access_token = create_access_token(user.id, expires_delta=access_token_expires)
    
    # Redirect back to frontend with the token
    # We use a query parameter 'token' which the frontend will look for
    redirect_url = f"{settings.frontend_url}/auth?token={access_token}"
    return RedirectResponse(url=redirect_url)


@router.get("/me", response_model=UserRead)
def get_me(current_user: Annotated[User, Depends(get_current_user)]) -> User:
    return current_user


def _token_for_user(user: User) -> dict:
    settings = get_settings()
    access_token_expires = timedelta(minutes=settings.access_token_expire_minutes)
    return {
        "access_token": create_access_token(user.id, expires_delta=access_token_expires),
        "token_type": "bearer",
    }


def _client_ip(request: Request) -> str:
    if request.client:
        return request.client.host
    return "unknown"
