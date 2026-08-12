from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field

class DataManagerTableInfo(BaseModel):
    """可管理数据表信息。"""

    schema_name: str
    table_name: str
    row_count: int
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
