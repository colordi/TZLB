from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from backend.services.pest_registry import (
    normalize_task_type,
    validate_pest_type as validate_registered_pest_type,
    validate_task_type as validate_registered_task_type,
)


PestType = str
TaskType = str


class WorkOrderRecord(BaseModel):
    """工作单单条记录。"""

    model_config = ConfigDict(extra="ignore", str_strip_whitespace=True)

    survey_date: str
    region: str = ""
    locality: str
    location_id: str
    location_name: str
    occurrence_position: str = ""
    total_insect_count: int | None = None
    damage_level: str = ""
    pest_name: str = ""
    host_plant: str = ""
    green_space_type: str = ""
    pest_hosts: str = ""
    damaged_plant_count: int | None = None
    web_nest_count: int | None = None
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
    output_format: Literal["doc", "docx"] | None = None
    records: list[WorkOrderRecord]

    @field_validator("pest_type")
    @classmethod
    def validate_pest_type(cls, value: str) -> str:
        return validate_registered_pest_type(value)

    @field_validator("task_type")
    @classmethod
    def normalize_task_type(cls, value: str) -> str:
        return normalize_task_type(value)

    @field_validator("records")
    @classmethod
    def validate_records(cls, value: list[WorkOrderRecord]) -> list[WorkOrderRecord]:
        if not value:
            raise ValueError("至少需要 1 条记录")
        return value

    @model_validator(mode="after")
    def validate_task_type(self) -> WorkOrderGenerateRequest:
        self.task_type = validate_registered_task_type(self.pest_type, self.task_type)
        return self


class MapViewSummary(BaseModel):
    """地图视图摘要。"""

    name: str
    columns: list[str]


class WhiteMothSiteCreateRequest(BaseModel):
    """美国白蛾点位新增请求。"""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    code: str = Field(min_length=1)
    site_name: str = ""
    longitude: float = Field(ge=-180, le=180)
    latitude: float = Field(ge=-90, le=90)

    @field_validator("code")
    @classmethod
    def normalize_code(cls, value: str) -> str:
        return value.strip().upper()


class WhiteMothSiteResponse(BaseModel):
    """美国白蛾点位新增响应。"""

    gid: int | None = None
    code: str
    locality: str
    site_name: str = ""
    longitude: float
    latitude: float


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
