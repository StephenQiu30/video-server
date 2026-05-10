import httpx
from datetime import timedelta
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import RedirectResponse
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.security import create_access_token, hash_password, verify_password
from app.db.session import get_db
from app.deps import get_current_user
from app.models import User
from app.schemas import Token, UserCreate, UserRead

router = APIRouter(prefix="/api/auth", tags=["auth"])


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


@router.get("/github/callback", response_model=Token)
async def github_callback(
    code: str,
    db: Annotated[Session, Depends(get_db)],
) -> dict:
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
            headers={"Accept": "application/json"},
        )
        token_data = token_res.json()
        gh_access_token = token_data.get("access_token")
        if not gh_access_token:
            raise HTTPException(status_code=400, detail="Failed to get GitHub access token")

        # 2. Get user info
        user_res = await client.get(
            "https://github.com/user",
            headers={"Authorization": f"token {gh_access_token}"},
        )
        gh_user = user_res.json()
        gh_id = str(gh_user.get("id"))
        
        # 3. Get primary email if not public
        email = gh_user.get("email")
        if not email:
            emails_res = await client.get(
                "https://github.com/user/emails",
                headers={"Authorization": f"token {gh_access_token}"},
            )
            emails = emails_res.json()
            primary_email = next((e["email"] for e in emails if e["primary"]), emails[0]["email"])
            email = primary_email

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
    return {"access_token": access_token, "token_type": "bearer"}


@router.get("/me", response_model=UserRead)
def get_me(current_user: Annotated[User, Depends(get_current_user)]) -> User:
    return current_user
