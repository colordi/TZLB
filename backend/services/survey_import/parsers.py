from __future__ import annotations

from datetime import date, datetime, timedelta
from typing import Any

from backend.services.survey_import.types import (
    EXCEL_DATETIME_EPOCH,
    EXCEL_EPOCH,
    USE_DEFAULT,
    ColumnMeta,
)


def normalize_header_value(value: Any) -> str:
    return str(value or "").strip()


def is_blank(value: Any) -> bool:
    return value is None or str(value).strip() == ""


def parse_excel_date(value: Any) -> date | None:
    if is_blank(value):
        return None
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    if isinstance(value, bool):
        raise ValueError("日期不能是布尔值")
    if isinstance(value, int) or isinstance(value, float):
        if isinstance(value, float) and not value.is_integer():
            raise ValueError("日期序列号必须是整数")
        return EXCEL_EPOCH + timedelta(days=int(value))

    text = str(value).strip()
    try:
        return date.fromisoformat(text[:10])
    except ValueError as exc:
        raise ValueError("日期格式必须是 YYYY-MM-DD 或 Excel 日期") from exc


def parse_excel_datetime(value: Any) -> datetime | None:
    if is_blank(value):
        return None
    if isinstance(value, datetime):
        return value.replace(tzinfo=None)
    if isinstance(value, date):
        return datetime.combine(value, datetime.min.time())
    if isinstance(value, bool):
        raise ValueError("时间不能是布尔值")
    if isinstance(value, int) or isinstance(value, float):
        return EXCEL_DATETIME_EPOCH + timedelta(seconds=round(float(value) * 86400))

    text = str(value).strip()
    try:
        return datetime.fromisoformat(text)
    except ValueError:
        try:
            return datetime.combine(date.fromisoformat(text[:10]), datetime.min.time())
        except ValueError as exc:
            raise ValueError("时间格式必须是 YYYY-MM-DD 或 ISO 日期时间") from exc


def parse_integer(value: Any) -> int | None:
    if is_blank(value):
        return None
    if isinstance(value, bool):
        raise ValueError("整数不能是布尔值")
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        if not value.is_integer():
            raise ValueError("整数列不能包含小数")
        return int(value)

    text = str(value).strip()
    if not text.removeprefix("-").isdigit():
        raise ValueError("整数列只能填写整数")
    return int(text)


def parse_text(value: Any) -> str | None:
    if is_blank(value):
        return None
    if isinstance(value, datetime):
        return value.isoformat(sep=" ", timespec="seconds")
    if isinstance(value, date):
        return value.isoformat()
    if isinstance(value, float) and value.is_integer():
        return str(int(value))
    return str(value).strip()


def parse_cell_value(column: ColumnMeta, value: Any) -> Any:
    if is_blank(value):
        if not column.is_nullable and column.has_default:
            return USE_DEFAULT
        return None

    if column.data_type == "date":
        return parse_excel_date(value)
    if column.data_type.startswith("timestamp"):
        return parse_excel_datetime(value)
    if column.data_type in {"integer", "bigint", "smallint"}:
        return parse_integer(value)
    text = parse_text(value)
    if text is not None and column.enum_labels and text not in column.enum_labels:
        raise ValueError(f"取值必须是：{'、'.join(column.enum_labels)}")
    return text
