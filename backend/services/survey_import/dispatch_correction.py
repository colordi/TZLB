from __future__ import annotations

import re
from datetime import datetime
from typing import Any

import asyncpg

from backend.db.postgres import quote_identifier
from backend.services.survey_import.parsers import is_blank
from backend.services.survey_import.types import (
    LEDGER_HISTORY_RULES,
    RECHECK_ABNORMAL_EVENT_TYPE,
    PreparedSheet,
    TableMeta,
)


def parse_column_default_value(column: ColumnMeta) -> Any:
    """从列默认值表达式中提取字面量（如 2026、'第一代'::text），提取不到返回 None。"""
    text = column.default.strip()
    if not text:
        return None
    match = re.match(r"^'(.*)'::", text)
    if match:
        return match.group(1)
    if text.isdigit():
        return int(text)
    return None


def normalize_history_key_value(value: Any) -> Any:
    if isinstance(value, bool):
        return str(value)
    if isinstance(value, (int, float)):
        return int(value)
    return str(value).strip()


def event_time_of(values: dict[str, Any]) -> datetime | None:
    value = values.get("事件时间")
    return value if isinstance(value, datetime) else None


async def correct_dispatch_event_types(
    connection: asyncpg.Connection,
    sheets: list[PreparedSheet],
    metadata: dict[str, TableMeta],
) -> None:
    """用户录入下派类事件但同组已存在历史事件时，把事件类型纠正为"复查异常"。

    历史 = 数据库已有事件 + 本文件中事件时间更早的行；分组键由
    LEDGER_HISTORY_RULES 定义（编号 + 年份/世代/虫害类型）。
    用户填写的防治、复查异常、复查合格一律信任，不做纠正。
    """
    for sheet in sheets:
        if sheet.table_name is None or sheet.table_name not in metadata:
            continue
        if sheet.errors:
            continue
        table_meta = metadata[sheet.table_name]
        rule = LEDGER_HISTORY_RULES.get((table_meta.schema_name, table_meta.name))
        if rule is None or not sheet.rows:
            continue
        group_columns, dispatch_types = rule

        codes = sorted(
            {
                str(row.values["编号"]).strip()
                for row in sheet.rows
                if not is_blank(row.values.get("编号"))
            }
        )
        if not codes:
            continue

        select_columns = list(dict.fromkeys([*group_columns, "事件类型", "事件时间"]))
        qualified_table = (
            f"{quote_identifier(table_meta.schema_name)}.{quote_identifier(table_meta.name)}"
        )
        history_rows = await connection.fetch(
            f"""
            SELECT {', '.join(quote_identifier(column) for column in select_columns)}
            FROM {qualified_table}
            WHERE {quote_identifier("编号")} = ANY($1::text[])
            """,
            codes,
        )

        def effective_group_key(values: dict[str, Any]) -> tuple[Any, ...] | None:
            key: list[Any] = []
            for column in group_columns:
                value = values.get(column)
                if is_blank(value):
                    value = parse_column_default_value(table_meta.columns[column])
                if is_blank(value) and column == "年份":
                    event_time = event_time_of(values)
                    if event_time is not None:
                        value = event_time.year
                if is_blank(value):
                    return None
                key.append(normalize_history_key_value(value))
            return tuple(key)

        histories: dict[tuple[Any, ...], list[tuple[str, Any]]] = {}
        for history_row in history_rows:
            event_type = history_row["事件类型"]
            if is_blank(event_type) or any(
                is_blank(history_row[column]) for column in group_columns
            ):
                continue
            key = tuple(
                normalize_history_key_value(history_row[column])
                for column in group_columns
            )
            histories.setdefault(key, []).append(
                (str(event_type).strip(), history_row["事件时间"])
            )

        ordered_rows = sorted(
            sheet.rows,
            key=lambda row: (
                event_time_of(row.values) is None,
                event_time_of(row.values) or datetime.min,
            ),
        )
        for row in ordered_rows:
            event_type = row.values.get("事件类型")
            key = effective_group_key(row.values)
            if key is None:
                continue
            current_time = event_time_of(row.values)
            if not is_blank(event_type) and str(event_type).strip() in dispatch_types:
                original = str(event_type).strip()
                qualifies = any(
                    h_type == original or h_type not in dispatch_types
                    for h_type, h_time in histories.get(key, [])
                    if h_time is None
                    or current_time is None
                    or h_time < current_time
                )
                if qualifies:
                    row.values["事件类型"] = RECHECK_ABNORMAL_EVENT_TYPE
                    row.conflict_values = tuple(
                        row.values[column] for column in table_meta.conflict_columns
                    )
                    sheet.warnings.append(
                        f"第 {row.row_number} 行：编号 {row.values.get('编号')} "
                        f"存在历史事件，事件类型由「{original}」纠正为"
                        f"「{RECHECK_ABNORMAL_EVENT_TYPE}」"
                    )
            if not is_blank(row.values.get("事件类型")):
                histories.setdefault(key, []).append(
                    (str(row.values["事件类型"]).strip(), current_time)
                )
