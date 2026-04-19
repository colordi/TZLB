from __future__ import annotations

from ipaddress import ip_address
from urllib.parse import urlsplit

from fastapi import Depends, HTTPException, Request, status

from backend.auth.security import parse_session_token
from backend.auth.store import get_active_user
from backend.config import get_settings


AUTH_REQUIRED_MESSAGE = "未登录或登录状态已失效"
LOCAL_AUTH_BYPASS_HEADER = "x-tzlb-local-auth-bypass"


def _extract_hostname(value: str | None) -> str | None:
    """从 URL 或 Host 头中提取主机名。"""

    if not value:
        return None

    parsed = urlsplit(value if "://" in value else f"//{value}", scheme="http")
    hostname = parsed.hostname
    if not hostname:
        return None
    return hostname.strip().lower()


def _is_loopback_hostname(hostname: str | None) -> bool:
    """判断主机名是否为本机回环地址。"""

    if not hostname:
        return False

    normalized = hostname.strip().strip("[]").lower()
    if normalized == "localhost":
        return True

    try:
        return ip_address(normalized).is_loopback
    except ValueError:
        return False


def _request_targets_localhost(request: Request) -> bool:
    """判断请求是否来自本机页面或本机直连接口。"""

    inspected_header = False
    for header_name in ("origin", "referer"):
        hostname = _extract_hostname(request.headers.get(header_name))
        if hostname is None:
            continue

        inspected_header = True
        if not _is_loopback_hostname(hostname):
            return False

    if inspected_header:
        return True

    host_header = _extract_hostname(request.headers.get("host"))
    client_host = request.client.host if request.client else None
    return _is_loopback_hostname(host_header) and _is_loopback_hostname(client_host)


def _build_local_bypass_user(settings) -> dict:
    """构造本机免登时返回的默认用户。"""

    username = settings.auth_default_admin_username.strip() or "local-dev"
    display_name = settings.auth_default_admin_display_name.strip() or username
    return {
        "id": 0,
        "username": username,
        "display_name": display_name,
        "is_active": True,
        "last_login_at": None,
    }


def _should_bypass_auth(request: Request, settings) -> bool:
    """仅在显式开启且请求明确来自本机时跳过认证。"""

    return (
        settings.auth_bypass_localhost
        and request.headers.get(LOCAL_AUTH_BYPASS_HEADER) == "1"
        and _request_targets_localhost(request)
    )


async def get_current_user(request: Request) -> dict:
    """从会话 Cookie 中解析当前用户。"""

    settings = get_settings()
    if _should_bypass_auth(request, settings):
        return _build_local_bypass_user(settings)

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
