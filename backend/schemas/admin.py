from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

class LayerMetadataItem(BaseModel):
    """图层元数据条目。"""

    model_config = ConfigDict(extra="forbid")

    layer_key: str = Field(min_length=1)
    layer_type: str = Field(pattern=r"^(view|reference)$")
    display_name: str | None = None
    sort_order: int = 0
    default_visible: bool = False
    is_enabled: bool = True
    default_filters: dict[str, str] = Field(default_factory=dict)


class LayerMetadataResponse(BaseModel):
    """图层元数据响应。"""

    id: int
    layer_key: str
    layer_type: str
    display_name: str | None = None
    sort_order: int
    default_visible: bool
    is_enabled: bool
    default_filters: dict[str, str] = Field(default_factory=dict)
    updated_at: str | None = None


class BatchUpdateLayersRequest(BaseModel):
    """批量更新图层元数据请求。"""

    model_config = ConfigDict(extra="forbid")

    items: list[LayerMetadataItem]


class CreateUserRequest(BaseModel):
    """创建用户请求。"""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    username: str = Field(min_length=1, max_length=100)
    password: str = Field(min_length=6, max_length=200)
    display_name: str = ""
    role: Literal["admin", "investigator"] = "investigator"


class UpdateUserRequest(BaseModel):
    """更新用户请求。"""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    display_name: str | None = None
    role: Literal["admin", "investigator"] | None = None
    is_active: bool | None = None


class ResetPasswordRequest(BaseModel):
    """重置密码请求。"""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    new_password: str = Field(min_length=6, max_length=200)


class AdminUserResponse(BaseModel):
    """管理后台用户信息响应。"""

    id: int
    username: str
    display_name: str
    role: str
    is_active: bool
    last_login_at: str | None = None
    created_at: str | None = None


class DashboardStatsResponse(BaseModel):
    """管理概览 KPI 数据。"""

    users: dict
    layers: dict
    database_views: int
    database_reference_layers: int


# ──────────────────────────────────────────────
#  Data Manager — 数据管理 API
# ──────────────────────────────────────────────
