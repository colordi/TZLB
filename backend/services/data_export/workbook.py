from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from io import BytesIO
from typing import Any

import asyncpg
from openpyxl import Workbook

from backend.db.postgres import quote_identifier
from backend.services.data_export.types import (
    ALLOWED_EXPORT_SCHEMAS,
    INVALID_SHEET_NAME_CHARS,
    MAX_SHEET_NAME_LENGTH,
    ExportTableMeta,
)


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

async def append_table_sheet(
    workbook: Workbook,
    connection: asyncpg.Connection,
    table: ExportTableMeta,
    sheet_name: str,
    where_clause: str | None = None,
    where_params: tuple[Any, ...] = (),
) -> None:
    worksheet = workbook.create_sheet(sheet_name)
    worksheet.append(list(table.columns))

    qualified_table = f"{quote_identifier(table.schema_name)}.{quote_identifier(table.table_name)}"
    column_sql = ", ".join(quote_identifier(column) for column in table.columns)

    if where_clause:
        rows = await connection.fetch(
            f"SELECT {column_sql} FROM {qualified_table} WHERE {where_clause}",
            *where_params,
        )
    else:
        rows = await connection.fetch(f"SELECT {column_sql} FROM {qualified_table}")

    for row in rows:
        worksheet.append([serialize_cell_value(row[column]) for column in table.columns])


def append_summary_sheet(
    workbook: Workbook,
    tables: list[ExportTableMeta],
    sheet_names: dict[tuple[str, str], str],
    exported_at: datetime,
    range_description: str = "survey, ledger 表和视图",
) -> None:
    worksheet = workbook.create_sheet("导出说明", 0)
    worksheet.append(["导出时间", exported_at.strftime("%Y-%m-%d %H:%M:%S")])
    worksheet.append(["导出范围", range_description])
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
