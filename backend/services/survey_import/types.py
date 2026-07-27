from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime
from typing import Any

ALLOWED_SCHEMAS = ("survey", "ledger")
AUTO_DEFAULT_MARKERS = ("nextval(", "generated")
EXCEL_EPOCH = date(1899, 12, 30)
EXCEL_DATETIME_EPOCH = datetime.combine(EXCEL_EPOCH, datetime.min.time())
RECHECK_ABNORMAL_EVENT_TYPE = "复查异常"

# 没有业务唯一键的流水表，冲突键统一硬编码为 (编号, 事件类型, 事件时间)，
# 插入时走 INSERT ... WHERE NOT EXISTS（不支持 ON CONFLICT）。
LEDGER_CONFLICT_COLUMNS = {
    ("ledger", "美国白蛾问题点位事件流水表"): ("编号", "事件类型", "事件时间"),
    ("ledger", "国槐尺蠖问题点位事件流水表"): ("编号", "事件类型", "事件时间"),
    ("ledger", "春尺蠖问题点位事件流水表"): ("编号", "事件类型", "事件时间"),
}
# id 既非 identity 也无默认值的流水表，由后端按 MAX(id)+1 分配。
BACKEND_GENERATED_ID_TABLES = {
    ("ledger", "美国白蛾问题点位事件流水表"),
    ("ledger", "国槐尺蠖问题点位事件流水表"),
}
# 历史对比纠正规则：(schema, 表名) -> (历史分组键, 下派类事件类型集合)。
# 用户录入下派类事件但同组已存在历史事件时，纠正为"复查异常"。
LEDGER_HISTORY_RULES = {
    ("ledger", "美国白蛾问题点位事件流水表"): (("编号", "年份", "世代"), {"调查下派"}),
    ("ledger", "国槐尺蠖问题点位事件流水表"): (
        ("编号", "年份", "世代"),
        {"历史预警下派", "幼虫调查下派"},
    ),
    ("ledger", "春尺蠖问题点位事件流水表"): (
        ("编号", "年份"),
        {"历史预警下派", "成虫调查下派", "幼虫调查下派"},
    ),
    ("ledger", "其他害虫问题点位事件流水表"): (("编号", "虫害类型", "年份"), {"调查下派"}),
}
LOCALITY_FIELD = "属地"
EVENT_TYPE_FIELD = "事件类型"
DAMAGED_PLANT_COUNT_FIELD = "受害株数"
DAMAGE_LEVEL_FIELD = "危害程度"
EMPTY_LOCALITY_LABEL = "未填写"
UNDAMAGED_LEVELS = frozenset({"", "白", "无需防治"})


@dataclass(frozen=True)
class ColumnMeta:
    name: str
    data_type: str
    udt_name: str
    is_nullable: bool
    default: str
    ordinal_position: int
    is_identity: bool = False
    enum_labels: tuple[str, ...] = ()

    @property
    def is_auto_generated(self) -> bool:
        normalized_default = self.default.lower()
        return self.is_identity or any(
            marker in normalized_default for marker in AUTO_DEFAULT_MARKERS
        )

    @property
    def has_default(self) -> bool:
        return self.default.strip() != ""


@dataclass(frozen=True)
class TableMeta:
    schema_name: str
    name: str
    columns: dict[str, ColumnMeta]
    conflict_columns: tuple[str, ...]
    supports_on_conflict: bool = True


@dataclass
class PreparedRow:
    row_number: int
    values: dict[str, Any]
    conflict_values: tuple[Any, ...]
    skipped_duplicate: bool = False


@dataclass
class PreparedSheet:
    sheet_name: str
    schema_name: str | None
    table_name: str | None
    row_count: int = 0
    valid_rows: int = 0
    inserted_rows: int = 0
    skipped_duplicate_rows: int = 0
    warnings: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    rows: list[PreparedRow] = field(default_factory=list)


class UseColumnDefault:
    pass


USE_DEFAULT = UseColumnDefault()
