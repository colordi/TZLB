from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal
from io import BytesIO
from typing import Any

import asyncpg
from openpyxl import Workbook

from backend.db.postgres import ensure_pool, quote_identifier


ALLOWED_EXPORT_SCHEMAS = ("survey", "ledger")
XLSX_MEDIA_TYPE = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
INVALID_SHEET_NAME_CHARS = set('[]:*?/\\')
MAX_SHEET_NAME_LENGTH = 31


@dataclass(frozen=True)
class ExportTableMeta:
    schema_name: str
    table_name: str
    object_type: str
    columns: tuple[str, ...]
    row_count: int

    @property
    def column_count(self) -> int:
        return len(self.columns)

    def to_public_dict(self) -> dict[str, Any]:
        return {
            "schema_name": self.schema_name,
            "table_name": self.table_name,
            "object_type": self.object_type,
            "column_count": self.column_count,
            "row_count": self.row_count,
        }


@dataclass(frozen=True)
class DataExportArtifact:
    filename: str
    media_type: str
    content: bytes


def validate_export_schema(schema_name: str) -> None:
    if schema_name not in ALLOWED_EXPORT_SCHEMAS:
        raise ValueError(f"不支持导出 schema：{schema_name}")


def normalize_sheet_name(value: str) -> str:
    normalized = "".join("_" if char in INVALID_SHEET_NAME_CHARS else char for char in value)
    normalized = normalized.strip().strip("'")
    return normalized or "导出表"


def build_unique_sheet_names(tables: list[ExportTableMeta]) -> dict[tuple[str, str], str]:
    used_names: set[str] = set()
    sheet_names: dict[tuple[str, str], str] = {}

    for table in tables:
        base_name = normalize_sheet_name(f"{table.schema_name}.{table.table_name}")
        candidate = base_name[:MAX_SHEET_NAME_LENGTH]
        suffix_index = 2
        while candidate in used_names:
            suffix = f"_{suffix_index}"
            candidate = f"{base_name[:MAX_SHEET_NAME_LENGTH - len(suffix)]}{suffix}"
            suffix_index += 1

        used_names.add(candidate)
        sheet_names[(table.schema_name, table.table_name)] = candidate

    return sheet_names


def serialize_cell_value(value: Any) -> Any:
    if value is None or isinstance(value, (str, int, float, bool, date, datetime, Decimal)):
        return value
    if isinstance(value, (bytes, bytearray, memoryview)):
        return bytes(value).hex()
    if isinstance(value, (list, tuple, dict)):
        return json.dumps(value, ensure_ascii=False, default=str)
    return str(value)


def build_export_filename(prefix: str, exported_at: datetime | None = None) -> str:
    timestamp = (exported_at or datetime.now()).strftime("%Y%m%d_%H%M%S")
    return f"{prefix}_{timestamp}.xlsx"


async def fetch_export_table_metadata(
    connection: asyncpg.Connection,
    schema_name: str | None = None,
    table_name: str | None = None,
) -> list[ExportTableMeta]:
    if schema_name is not None:
        validate_export_schema(schema_name)

    rows = await connection.fetch(
        """
        SELECT
            t.table_schema,
            t.table_name,
            CASE t.table_type
                WHEN 'VIEW' THEN 'view'
                ELSE 'table'
            END AS object_type,
            ARRAY_AGG(c.column_name ORDER BY c.ordinal_position) AS columns
        FROM information_schema.tables AS t
        JOIN information_schema.columns AS c
          ON c.table_schema = t.table_schema
         AND c.table_name = t.table_name
        WHERE t.table_schema = ANY($1::text[])
          AND t.table_type IN ('BASE TABLE', 'VIEW')
          AND ($2::text IS NULL OR t.table_schema = $2)
          AND ($3::text IS NULL OR t.table_name = $3)
        GROUP BY t.table_schema, t.table_name, t.table_type
        ORDER BY
            CASE t.table_schema WHEN 'survey' THEN 0 WHEN 'ledger' THEN 1 ELSE 2 END,
            CASE t.table_type WHEN 'BASE TABLE' THEN 0 WHEN 'VIEW' THEN 1 ELSE 2 END,
            t.table_name
        """,
        list(ALLOWED_EXPORT_SCHEMAS),
        schema_name,
        table_name,
    )

    tables: list[ExportTableMeta] = []
    for row in rows:
        qualified_table = (
            f"{quote_identifier(row['table_schema'])}.{quote_identifier(row['table_name'])}"
        )
        count_row = await connection.fetchrow(
            f"SELECT COUNT(*) AS row_count FROM {qualified_table}"
        )
        tables.append(
            ExportTableMeta(
                schema_name=row["table_schema"],
                table_name=row["table_name"],
                object_type=row["object_type"],
                columns=tuple(row["columns"] or ()),
                row_count=int(count_row["row_count"] if count_row else 0),
            )
        )

    return tables


async def list_export_tables() -> list[dict[str, Any]]:
    pool = await ensure_pool()
    async with pool.acquire() as connection:
        tables = await fetch_export_table_metadata(connection)
    return [table.to_public_dict() for table in tables]


async def get_export_table_meta(
    connection: asyncpg.Connection,
    schema_name: str,
    table_name: str,
) -> ExportTableMeta:
    tables = await fetch_export_table_metadata(
        connection,
        schema_name=schema_name,
        table_name=table_name,
    )
    if not tables:
        raise ValueError(f"表或视图不存在或不允许导出：{schema_name}.{table_name}")
    return tables[0]


async def append_table_sheet(
    workbook: Workbook,
    connection: asyncpg.Connection,
    table: ExportTableMeta,
    sheet_name: str,
) -> None:
    worksheet = workbook.create_sheet(sheet_name)
    worksheet.append(list(table.columns))

    qualified_table = f"{quote_identifier(table.schema_name)}.{quote_identifier(table.table_name)}"
    column_sql = ", ".join(quote_identifier(column) for column in table.columns)
    rows = await connection.fetch(f"SELECT {column_sql} FROM {qualified_table}")

    for row in rows:
        worksheet.append([serialize_cell_value(row[column]) for column in table.columns])


def append_summary_sheet(
    workbook: Workbook,
    tables: list[ExportTableMeta],
    sheet_names: dict[tuple[str, str], str],
    exported_at: datetime,
) -> None:
    worksheet = workbook.create_sheet("导出说明", 0)
    worksheet.append(["导出时间", exported_at.strftime("%Y-%m-%d %H:%M:%S")])
    worksheet.append(["导出范围", "survey, ledger 表和视图"])
    worksheet.append([])
    worksheet.append(["schema", "名称", "类型", "sheet 名", "记录数", "字段数"])
    for table in tables:
        worksheet.append(
            [
                table.schema_name,
                table.table_name,
                "视图" if table.object_type == "view" else "表",
                sheet_names[(table.schema_name, table.table_name)],
                table.row_count,
                table.column_count,
            ]
        )


def workbook_to_bytes(workbook: Workbook) -> bytes:
    output = BytesIO()
    workbook.save(output)
    return output.getvalue()


async def export_all_tables() -> DataExportArtifact:
    exported_at = datetime.now()
    workbook = Workbook(write_only=True)

    pool = await ensure_pool()
    async with pool.acquire() as connection:
        tables = await fetch_export_table_metadata(connection)
        if not tables:
            raise ValueError("没有可导出的 survey 或 ledger 表或视图")

        sheet_names = build_unique_sheet_names(tables)
        append_summary_sheet(workbook, tables, sheet_names, exported_at)
        for table in tables:
            await append_table_sheet(
                workbook,
                connection,
                table,
                sheet_names[(table.schema_name, table.table_name)],
            )

    return DataExportArtifact(
        filename=build_export_filename("调查数据导出", exported_at),
        media_type=XLSX_MEDIA_TYPE,
        content=workbook_to_bytes(workbook),
    )


async def export_single_table(schema_name: str, table_name: str) -> DataExportArtifact:
    exported_at = datetime.now()
    workbook = Workbook(write_only=True)

    pool = await ensure_pool()
    async with pool.acquire() as connection:
        table = await get_export_table_meta(connection, schema_name, table_name)
        sheet_name = build_unique_sheet_names([table])[(table.schema_name, table.table_name)]
        await append_table_sheet(workbook, connection, table, sheet_name)

    return DataExportArtifact(
        filename=build_export_filename(f"{schema_name}_{table_name}", exported_at),
        media_type=XLSX_MEDIA_TYPE,
        content=workbook_to_bytes(workbook),
    )
