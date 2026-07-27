from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class AuthenticatedUser(BaseModel):
    """已登录用户信息。"""

    id: int
    username: str
    display_name: str
    role: Literal["admin", "investigator"]
    is_active: bool
    last_login_at: str | None = None


class LoginRequest(BaseModel):
    """登录请求。"""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    username: str = Field(min_length=1)
    password: str = Field(min_length=1)
    remember_me: bool = False


class AuthSessionResponse(BaseModel):
    """认证会话响应。"""

    user: AuthenticatedUser
