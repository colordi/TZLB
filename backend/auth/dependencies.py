from __future__ import annotations

from fastapi import Depends, HTTPException, Request, status

from backend.auth.security import parse_session_token
from backend.auth.store import get_active_user
from backend.config import get_settings


AUTH_REQUIRED_MESSAGE = "未登录或登录状态已失效"


async def get_current_user(request: Request) -> dict:
    """从会话 Cookie 中解析当前用户。"""

    settings = get_settings()
    session_token = request.cookies.get(settings.auth_cookie_name)
    if not session_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=AUTH_REQUIRED_MESSAGE,
        )

    payload = parse_session_token(session_token, settings.auth_secret_key)
    if payload is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=AUTH_REQUIRED_MESSAGE,
        )

    user = await get_active_user(payload.username)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=AUTH_REQUIRED_MESSAGE,
        )

    return user


async def require_authenticated_user(current_user: dict = Depends(get_current_user)) -> dict:
    """要求当前请求必须处于已登录状态。"""

    return current_user
