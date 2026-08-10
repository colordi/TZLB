from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field, field_validator

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


class GenericSiteCreateRequest(BaseModel):
    """任务视图通用点位新增请求。"""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    view_name: str = Field(min_length=1)
    code: str = Field(min_length=1)
    site_name: str = ""
    locality: str | None = None
    longitude: float = Field(ge=-180, le=180)
    latitude: float = Field(ge=-90, le=90)

    @field_validator("code")
    @classmethod
    def normalize_code(cls, value: str) -> str:
        return value.strip().upper()

    @field_validator("view_name")
    @classmethod
    def normalize_view_name(cls, value: str) -> str:
        return value.strip()


class GenericSiteCodeHintResponse(BaseModel):
    """通用点位编号提示响应。"""

    prefix: str
    locality: str | None = None
    latest_code: str | None = None
    latest_serial: int | None = None
    suggested_next_code: str | None = None


class GenericSiteResponse(BaseModel):
    """通用点位新增响应。"""

    gid: int | None = None
    code: str
    locality: str
    site_name: str = ""
    longitude: float
    latitude: float
    base_table: str
    view_name: str


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
