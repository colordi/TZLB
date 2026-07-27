from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from backend.services.pest_registry import (
    normalize_task_type,
    validate_pest_type as validate_registered_pest_type,
    validate_generation as validate_registered_generation,
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

    @field_validator("survey_date")
    @classmethod
    def validate_survey_date(cls, value: str) -> str:
        normalized = (value or "").strip()
        if not normalized:
            raise ValueError("调查日期不能为空")
        try:
            datetime.strptime(normalized, "%Y-%m-%d")
        except ValueError as exc:
            raise ValueError("调查日期必须是 YYYY-MM-DD 格式") from exc
        return normalized


class WorkOrderGenerateRequest(BaseModel):
    """工作单生成请求。"""

    model_config = ConfigDict(extra="forbid")

    pest_type: PestType
    task_type: TaskType
    task: str = ""
    year: int = Field(default_factory=lambda: datetime.now().year)
    generation: str | None = None
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

    @model_validator(mode="after")
    def validate_generation(self) -> WorkOrderGenerateRequest:
        self.generation = validate_registered_generation(self.pest_type, self.generation)
        return self


class WorkOrderBatchGenerateRequest(BaseModel):
    """工作单批量生成请求。"""

    model_config = ConfigDict(extra="forbid")

    pest_type: PestType
    task_type: TaskType
    task: str = ""
    year: int = Field(default_factory=lambda: datetime.now().year)
    generation: str | None = None
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
    def validate_task_type(self) -> WorkOrderBatchGenerateRequest:
        self.task_type = validate_registered_task_type(self.pest_type, self.task_type)
        return self

    @model_validator(mode="after")
    def validate_generation(self) -> WorkOrderBatchGenerateRequest:
        self.generation = validate_registered_generation(self.pest_type, self.generation)
        return self

    @model_validator(mode="after")
    def validate_batch_size(self) -> WorkOrderBatchGenerateRequest:
        from backend.config import get_settings

        max_records = get_settings().workorder_batch_max_records
        if len(self.records) > max_records:
            raise ValueError(f"单次批量导出最多 {max_records} 条记录")
        return self


class WorkOrderBatchJobCreateResponse(BaseModel):
    """批量导出任务创建响应。"""

    job_id: str
    total: int
    status: str


class WorkOrderBatchJobStatusResponse(BaseModel):
    """批量导出任务进度响应。"""

    job_id: str
    status: str
    current: int
    total: int
    percent: int
    phase: str
    message: str
    error: str | None = None
    filename: str | None = None
    ready_for_download: bool = False


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


class WhiteMothSiteCodeHintResponse(BaseModel):
    """美国白蛾点位编号提示响应。"""

    prefix: str
    locality: str
    latest_code: str | None = None
    latest_serial: int | None = None
    suggested_next_code: str | None = None


class WhiteMothSiteResponse(BaseModel):
    """美国白蛾点位新增响应。"""

    gid: int | None = None
    code: str
    locality: str
    site_name: str = ""
    longitude: float
    latitude: float


class WhiteMothSiteDeleteCheckResponse(BaseModel):
    """美国白蛾点位删除前检查响应。"""

    code: str
    exists: bool
    site_name: str | None = None
    locality: str | None = None
    longitude: float | None = None
    latitude: float | None = None
    survey_record_count: int = 0


class WhiteMothSiteDeleteResponse(BaseModel):
    """美国白蛾点位删除响应。"""

    code: str
    site_name: str = ""
    locality: str = ""
    longitude: float
    latitude: float
    survey_record_count: int = 0


class OtherPestSiteCreateRequest(BaseModel):
    """其他害虫点位新增请求。"""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    code: str = Field(min_length=1)
    site_name: str = ""
    locality: str = Field(min_length=1)
    longitude: float = Field(ge=-180, le=180)
    latitude: float = Field(ge=-90, le=90)

    @field_validator("code")
    @classmethod
    def normalize_code(cls, value: str) -> str:
        return value.strip().upper()


class OtherPestSiteCodeHintResponse(BaseModel):
    """其他害虫点位编号提示响应。"""

    prefix: str
    latest_code: str | None = None
    latest_serial: int | None = None
    suggested_next_code: str | None = None


class OtherPestSiteResponse(BaseModel):
    """其他害虫点位新增响应。"""

    gid: int | None = None
    code: str
    locality: str
    site_name: str = ""
    longitude: float
    latitude: float


class OtherPestSiteDeleteCheckResponse(BaseModel):
    """其他害虫点位删除前检查响应。"""

    code: str
    exists: bool
    site_name: str | None = None
    locality: str | None = None
    longitude: float | None = None
    latitude: float | None = None
    survey_record_count: int = 0


class OtherPestSiteDeleteResponse(BaseModel):
    """其他害虫点位删除响应。"""

    code: str
    site_name: str = ""
    locality: str = ""
    longitude: float | None = None
    latitude: float | None = None
    survey_record_count: int = 0


class OperationLogItem(BaseModel):
    """点位操作日志条目。"""

    id: int
    occurred_at: str | None = None
    action: str
    operator_id: int | None = None
    operator_username: str
    operator_display_name: str
    operator_role: str
    site_code: str
    site_name: str = ""
    locality: str = ""
    longitude: float | None = None
    latitude: float | None = None
    survey_record_count: int = 0


class OperationLogListResponse(BaseModel):
    """点位操作日志列表响应。"""

    items: list[OperationLogItem]
    total: int


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


# ──────────────────────────────────────────────
#  Admin — Dashboard API
# ──────────────────────────────────────────────


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


class DataManagerTableInfo(BaseModel):
    """可管理数据表信息。"""

    schema_name: str
    table_name: str
    row_estimate: int
    has_primary_key: bool
    primary_key: list[str] = Field(default_factory=list)


class DataManagerColumnInfo(BaseModel):
    """数据表列元数据。"""

    name: str
    data_type: str
    is_nullable: bool
    has_default: bool
    is_primary_key: bool
    is_readonly: bool
    is_geometry: bool
    input_kind: str
    enum_labels: list[str] = Field(default_factory=list)


class DataManagerRowsResponse(BaseModel):
    """分页行数据响应。"""

    rows: list[dict]
    total: int
    page: int
    page_size: int


class DataManagerRowCreateRequest(BaseModel):
    """新增记录请求。"""

    model_config = ConfigDict(extra="forbid")

    values: dict[str, Any] = Field(default_factory=dict)


class DataManagerRowUpdateRequest(BaseModel):
    """更新记录请求：pk 定位行，values 为变更字段。"""

    model_config = ConfigDict(extra="forbid")

    pk: dict[str, Any]
    values: dict[str, Any]


class DataManagerRowDeleteRequest(BaseModel):
    """删除记录请求：pk 定位行。"""

    model_config = ConfigDict(extra="forbid")

    pk: dict[str, Any]


class DataManagerChangeLogItem(BaseModel):
    """数据变更日志条目。"""

    id: int
    occurred_at: str | None = None
    action: str
    operator_id: int | None = None
    operator_username: str
    operator_display_name: str
    schema_name: str
    table_name: str
    pk: dict[str, Any] = Field(default_factory=dict)
    before: dict[str, Any] | None = None
    after: dict[str, Any] | None = None


class DataManagerChangeLogListResponse(BaseModel):
    """数据变更日志列表响应。"""

    items: list[DataManagerChangeLogItem]
    total: int
