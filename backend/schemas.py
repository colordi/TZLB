from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator


PestType = Literal["春尺蠖", "国槐尺蠖", "其他害虫"]
TaskType = Literal["春尺蠖防治", "国槐尺蠖防治", "其他害虫防治"]


class WorkOrderRecord(BaseModel):
    """工作单单条记录。"""

    model_config = ConfigDict(extra="ignore", str_strip_whitespace=True)

    survey_date: str
    region: str = ""
    town_or_street: str
    location_id: str
    location_name: str
    occurrence_position: str = ""
    total_insect_count: int | None = None
    damage_level: str = ""
    pest_name: str = ""
    host_plant: str = ""
    report_time: str = ""
    description: str
    note: str = ""
    plot_type: str = ""
    serial_number: int | None = Field(default=None, ge=1, le=999)
    images: list[str] = Field(default_factory=list)

    @field_validator("images")
    @classmethod
    def validate_images(cls, value: list[str]) -> list[str]:
        if len(value) > 4:
            raise ValueError("单条记录最多上传 4 张图片")
        return value


class WorkOrderGenerateRequest(BaseModel):
    """工作单生成请求。"""

    model_config = ConfigDict(extra="forbid")

    pest_type: PestType
    task_type: TaskType
    task: str = ""
    records: list[WorkOrderRecord]

    @field_validator("records")
    @classmethod
    def validate_records(cls, value: list[WorkOrderRecord]) -> list[WorkOrderRecord]:
        if not value:
            raise ValueError("至少需要 1 条记录")
        return value


class MapViewSummary(BaseModel):
    """地图视图摘要。"""

    name: str
    columns: list[str]


class AuthenticatedUser(BaseModel):
    """已登录用户信息。"""

    id: int
    username: str
    display_name: str
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
