from __future__ import annotations

from datetime import timedelta

from fastapi import APIRouter, Depends, HTTPException, Response, status

from backend.auth.dependencies import require_authenticated_user
from backend.auth.security import build_session_token
from backend.auth.store import authenticate_user
from backend.config import get_settings
from backend.schemas import AuthSessionResponse, LoginRequest


router = APIRouter()


@router.post("/login", response_model=AuthSessionResponse, summary="用户名密码登录")
async def login(payload: LoginRequest, response: Response) -> AuthSessionResponse:
    user = await authenticate_user(payload.username, payload.password)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="用户名或密码错误",
        )

    settings = get_settings()
    session_lifetime = (
        timedelta(days=settings.auth_remember_ttl_days)
        if payload.remember_me
        else timedelta(hours=settings.auth_session_ttl_hours)
    )
    session_token, _ = build_session_token(
        username=user["username"],
        secret_key=settings.auth_secret_key,
        lifetime=session_lifetime,
    )
    max_age = int(session_lifetime.total_seconds())
    response.set_cookie(
        key=settings.auth_cookie_name,
        value=session_token,
        max_age=max_age,
        expires=max_age,
        path="/",
        secure=settings.auth_cookie_secure,
        httponly=True,
        samesite="lax",
    )
    return AuthSessionResponse(user=user)


@router.get("/me", response_model=AuthSessionResponse, summary="读取当前登录用户")
async def me(
    current_user: dict = Depends(require_authenticated_user),
) -> AuthSessionResponse:
    return AuthSessionResponse(user=current_user)


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT, summary="退出登录")
async def logout(response: Response) -> Response:
    settings = get_settings()
    response.status_code = status.HTTP_204_NO_CONTENT
    response.delete_cookie(
        key=settings.auth_cookie_name,
        path="/",
        secure=settings.auth_cookie_secure,
        httponly=True,
        samesite="lax",
    )
    return response
