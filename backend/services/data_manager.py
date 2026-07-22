"""数据管理模块的元数据解析与值校验逻辑（可独立单测）。"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal
from typing import Any

import asyncpg


MANAGEABLE_SCHEMAS = ("survey", "ledger", "sites")
GEOMETRY_UDT_NAMES = {"geometry", "geography"}
AUTO_DEFAULT_MARKERS = ("nextval(", "generated")

TEXT_DATA_TYPES = {
    "character varying",
    "character",
    "text",
    "name",
    "USER-DEFINED",
}
INTEGER_DATA_TYPES = {"integer", "bigint", "smallint"}
FLOAT_DATA_TYPES = {"double precision", "real", "numeric"}


@dataclass(frozen=True)
class ManagedColumnMeta:
    name: str
    data_type: str
    udt_name: str
    is_nullable: bool
    default: str
    ordinal_position: int
    is_identity: bool = False
    is_primary_key: bool = False
    enum_labels: tuple[str, ...] = ()

    @property
    def is_geometry(self) -> bool:
        return self.udt_name in GEOMETRY_UDT_NAMES

    @property
    def is_auto_generated(self) -> bool:
        normalized_default = self.default.lower()
        return self.is_identity or any(
            marker in normalized_default for marker in AUTO_DEFAULT_MARKERS
        )

    @property
    def has_default(self) -> bool:
        return self.default.strip() != ""

    @property
    def is_readonly(self) -> bool:
        """几何列和自增列不在网页表单中编辑。"""

        return self.is_geometry or self.is_auto_generated

    @property
    def input_kind(self) -> str:
        """前端表单渲染提示：text / textarea / number / date / datetime / bool / select。"""

        if self.enum_labels:
            return "select"
        if self.data_type == "date":
            return "date"
        if self.data_type.startswith("timestamp"):
            return "datetime"
        if self.data_type in INTEGER_DATA_TYPES or self.data_type in FLOAT_DATA_TYPES:
            return "number"
        if self.data_type == "boolean":
            return "bool"
        return "text"


@dataclass(frozen=True)
class ManagedTableMeta:
    schema_name: str
    name: str
    columns: tuple[ManagedColumnMeta, ...]
    primary_key: tuple[str, ...]

    @property
    def qualified_name(self) -> str:
        return f'"{self.schema_name}"."{self.name}"'

    @property
    def selectable_columns(self) -> tuple[ManagedColumnMeta, ...]:
        return tuple(column for column in self.columns if not column.is_geometry)

    def get_column(self, name: str) -> ManagedColumnMeta | None:
        for column in self.columns:
            if column.name == name:
                return column
        return None


async def fetch_managed_table_metadata(
    connection: asyncpg.Connection,
) -> dict[tuple[str, str], ManagedTableMeta]:
    """读取 survey/ledger/sites 下所有基表的列与主键元数据。"""

    column_rows = await connection.fetch(
        """
        SELECT
            c.table_schema,
            c.table_name,
            c.ordinal_position,
            c.column_name,
            c.data_type,
            c.udt_name,
            c.is_nullable,
            c.is_identity,
            COALESCE(c.column_default, '') AS column_default
        FROM information_schema.columns AS c
        JOIN information_schema.tables AS t
          ON t.table_schema = c.table_schema
         AND t.table_name = c.table_name
        WHERE c.table_schema = ANY($1::text[])
          AND t.table_type = 'BASE TABLE'
        ORDER BY c.table_schema, c.table_name, c.ordinal_position
        """,
        list(MANAGEABLE_SCHEMAS),
    )
    pk_rows = await connection.fetch(
        """
        SELECT
            tc.table_schema,
            tc.table_name,
            ARRAY_AGG(kcu.column_name ORDER BY kcu.ordinal_position) AS columns
        FROM information_schema.table_constraints AS tc
        JOIN information_schema.key_column_usage AS kcu
          ON kcu.constraint_schema = tc.constraint_schema
         AND kcu.constraint_name = tc.constraint_name
         AND kcu.table_schema = tc.table_schema
         AND kcu.table_name = tc.table_name
        WHERE tc.table_schema = ANY($1::text[])
          AND tc.constraint_type = 'PRIMARY KEY'
        GROUP BY tc.table_schema, tc.table_name
        """,
        list(MANAGEABLE_SCHEMAS),
    )
    enum_rows = await connection.fetch(
        """
        SELECT t.typname, e.enumlabel
        FROM pg_type AS t
        JOIN pg_enum AS e
          ON e.enumtypid = t.oid
        ORDER BY t.typname, e.enumsortorder
        """
    )

    enum_labels_by_type: dict[str, list[str]] = {}
    for row in enum_rows:
        enum_labels_by_type.setdefault(row["typname"], []).append(row["enumlabel"])

    pk_by_table: dict[tuple[str, str], tuple[str, ...]] = {}
    for row in pk_rows:
        pk_by_table[(row["table_schema"], row["table_name"])] = tuple(row["columns"] or ())

    columns_by_table: dict[tuple[str, str], list[ManagedColumnMeta]] = {}
    for row in column_rows:
        table_key = (row["table_schema"], row["table_name"])
        primary_key = pk_by_table.get(table_key, ())
        columns_by_table.setdefault(table_key, []).append(
            ManagedColumnMeta(
                name=row["column_name"],
                data_type=row["data_type"],
                udt_name=row["udt_name"],
                is_nullable=row["is_nullable"] == "YES",
                default=row["column_default"] or "",
                ordinal_position=row["ordinal_position"],
                is_identity=row["is_identity"] == "YES",
                is_primary_key=row["column_name"] in primary_key,
                enum_labels=tuple(enum_labels_by_type.get(row["udt_name"], ())),
            )
        )

    metadata: dict[tuple[str, str], ManagedTableMeta] = {}
    for (schema_name, table_name), columns in columns_by_table.items():
        metadata[(schema_name, table_name)] = ManagedTableMeta(
            schema_name=schema_name,
            name=table_name,
            columns=tuple(columns),
            primary_key=pk_by_table.get((schema_name, table_name), ()),
        )
    return metadata


def get_table_meta(
    metadata: dict[tuple[str, str], ManagedTableMeta],
    schema_name: str,
    table_name: str,
) -> ManagedTableMeta:
    """校验 schema/表名合法性并返回元数据，非法时抛 ValueError。"""

    if schema_name not in MANAGEABLE_SCHEMAS:
        raise ValueError(f"不允许访问 schema：{schema_name}")
    meta = metadata.get((schema_name, table_name))
    if meta is None:
        raise ValueError(f"数据表不存在：{schema_name}.{table_name}")
    return meta


def _is_blank(value: Any) -> bool:
    return value is None or (isinstance(value, str) and value.strip() == "")


def coerce_value(column: ManagedColumnMeta, value: Any) -> Any:
    """把前端提交的 JSON 值按列类型转换为可写库的值，非法时抛 ValueError。"""

    if _is_blank(value):
        return None

    if column.data_type == "date":
        if isinstance(value, datetime):
            return value.date()
        if isinstance(value, date):
            return value
        try:
            return date.fromisoformat(str(value).strip()[:10])
        except ValueError as exc:
            raise ValueError(f"列「{column.name}」日期格式必须是 YYYY-MM-DD") from exc

    if column.data_type.startswith("timestamp"):
        if isinstance(value, datetime):
            return value
        if isinstance(value, date):
            return datetime.combine(value, datetime.min.time())
        text = str(value).strip()
        try:
            return datetime.fromisoformat(text)
        except ValueError:
            try:
                return datetime.combine(date.fromisoformat(text[:10]), datetime.min.time())
            except ValueError as exc:
                raise ValueError(f"列「{column.name}」时间格式必须是 ISO 日期时间") from exc

    if column.data_type in INTEGER_DATA_TYPES:
        if isinstance(value, bool):
            raise ValueError(f"列「{column.name}」必须是整数")
        if isinstance(value, int):
            return value
        if isinstance(value, float):
            if not value.is_integer():
                raise ValueError(f"列「{column.name}」必须是整数")
            return int(value)
        text = str(value).strip()
        try:
            return int(text)
        except ValueError as exc:
            raise ValueError(f"列「{column.name}」必须是整数") from exc

    if column.data_type in FLOAT_DATA_TYPES:
        if isinstance(value, bool):
            raise ValueError(f"列「{column.name}」必须是数字")
        if isinstance(value, (int, float)):
            return value
        try:
            return float(str(value).strip())
        except ValueError as exc:
            raise ValueError(f"列「{column.name}」必须是数字") from exc

    if column.data_type == "boolean":
        if isinstance(value, bool):
            return value
        text = str(value).strip().lower()
        if text in {"true", "1", "是", "yes"}:
            return True
        if text in {"false", "0", "否", "no"}:
            return False
        raise ValueError(f"列「{column.name}」必须是布尔值")

    text = str(value).strip()
    if column.enum_labels and text not in column.enum_labels:
        raise ValueError(f"列「{column.name}」取值必须是：{'、'.join(column.enum_labels)}")
    return text


def validate_insert_values(
    table_meta: ManagedTableMeta, values: dict[str, Any]
) -> dict[str, Any]:
    """校验新增记录：拒绝只读列，补齐必填校验，返回转换后的值。"""

    cleaned: dict[str, Any] = {}
    for name, raw in values.items():
        column = table_meta.get_column(name)
        if column is None:
            raise ValueError(f"列不存在：{name}")
        if column.is_readonly:
            raise ValueError(f"列「{name}」由系统自动生成，不能填写")
        cleaned[name] = coerce_value(column, raw)

    for column in table_meta.columns:
        if column.is_readonly or column.is_nullable or column.has_default:
            continue
        if cleaned.get(column.name) is None:
            raise ValueError(f"列「{column.name}」为必填项")
    return cleaned


def validate_update_values(
    table_meta: ManagedTableMeta, values: dict[str, Any]
) -> dict[str, Any]:
    """校验更新记录：只允许修改非主键、非只读列。"""

    if not values:
        raise ValueError("没有需要更新的字段")
    cleaned: dict[str, Any] = {}
    for name, raw in values.items():
        column = table_meta.get_column(name)
        if column is None:
            raise ValueError(f"列不存在：{name}")
        if column.is_primary_key:
            raise ValueError(f"主键列「{name}」不允许修改")
        if column.is_readonly:
            raise ValueError(f"列「{name}」由系统自动生成，不能修改")
        cleaned[name] = coerce_value(column, raw)
    return cleaned


def validate_pk_values(
    table_meta: ManagedTableMeta, pk: dict[str, Any]
) -> dict[str, Any]:
    """校验主键定位值：必须完整覆盖主键列。"""

    if not table_meta.primary_key:
        raise ValueError(f"表 {table_meta.schema_name}.{table_meta.name} 没有主键，不支持该操作")
    cleaned: dict[str, Any] = {}
    for name in table_meta.primary_key:
        column = table_meta.get_column(name)
        raw = pk.get(name)
        if _is_blank(raw):
            raise ValueError(f"缺少主键列「{name}」的值")
        cleaned[name] = coerce_value(column, raw)
    extra = set(pk) - set(table_meta.primary_key)
    if extra:
        raise ValueError(f"存在非主键列：{'、'.join(sorted(extra))}")
    return cleaned


def serialize_value(value: Any) -> Any:
    """把 asyncpg 返回的值转成 JSON 可序列化形式。"""

    if isinstance(value, datetime):
        return value.isoformat(sep=" ", timespec="seconds")
    if isinstance(value, date):
        return value.isoformat()
    if isinstance(value, Decimal):
        return float(value)
    return value


def serialize_row(row: asyncpg.Record | dict[str, Any]) -> dict[str, Any]:
    return {key: serialize_value(value) for key, value in dict(row).items()}
