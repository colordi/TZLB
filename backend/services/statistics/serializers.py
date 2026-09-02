from __future__ import annotations

from datetime import date
from typing import Any

from backend.services.statistics.sql_daily import WHITE_MOTH_ROW_FIELD_MAP
from backend.services.statistics.sql_locality import (
    WHITE_MOTH_LOCALITY_ORDER,
    WHITE_MOTH_SEVERE_PLANT_THRESHOLD,
)


def serialize_daily_value(value: Any) -> Any:
    if isinstance(value, date):
        return value.isoformat()
    return value


def serialize_white_moth_daily_row(row: Any) -> dict[str, Any]:
    return {
        public_key: serialize_daily_value(row[chinese_key])
        for public_key, chinese_key in WHITE_MOTH_ROW_FIELD_MAP
    }

def _completion_rate(completed_points: int, damaged_points: int) -> float:
    if damaged_points <= 0:
        return 0.0
    return round(completed_points / damaged_points * 100, 1)


def serialize_locality_summary_row(row: Any) -> dict[str, Any]:
    damaged_points = int(row["damaged_points"] or 0)
    completed_points = int(row["completed_points"] or 0)
    return {
        "locality": row["locality"],
        "damaged_points": damaged_points,
        "damaged_plants": int(row["damaged_plants"] or 0),
        "completed_points": completed_points,
        "completion_rate": _completion_rate(completed_points, damaged_points),
        "severe_points": int(row["severe_points"] or 0),
        "unfeedback_points": int(row["unfeedback_points"] or 0),
        "collab_points": int(row["collab_points"] or 0),
        "unfeedback_sites": [],
    }


def serialize_unfeedback_site_row(row: Any) -> dict[str, Any]:
    return {
        "code": row["code"] or "",
        "name": row["name"] or "--",
    }


def merge_locality_summary_rows(
    rows: list[Any],
    unfeedback_site_rows: list[Any] | None = None,
) -> list[dict[str, Any]]:
    by_locality = {
        serialized["locality"]: serialized
        for serialized in (serialize_locality_summary_row(row) for row in rows)
    }
    empty = {
        "damaged_points": 0,
        "damaged_plants": 0,
        "completed_points": 0,
        "completion_rate": 0.0,
        "severe_points": 0,
        "unfeedback_points": 0,
        "collab_points": 0,
        "unfeedback_sites": [],
    }

    unfeedback_by_locality: dict[str, list[dict[str, Any]]] = {}
    for row in unfeedback_site_rows or []:
        locality = row["locality"]
        unfeedback_by_locality.setdefault(locality, []).append(
            serialize_unfeedback_site_row(row)
        )

    localities: list[dict[str, Any]] = []
    for locality in WHITE_MOTH_LOCALITY_ORDER:
        item = {"locality": locality, **by_locality.get(locality, empty)}
        sites = unfeedback_by_locality.get(locality, [])
        item["unfeedback_sites"] = sites
        # 以名单长度为准，避免汇总与明细偶发不一致
        item["unfeedback_points"] = len(sites) if sites else int(item.get("unfeedback_points") or 0)
        localities.append(item)
    return localities


def _parse_as_of_date(as_of_date: date | str | None) -> date:
    if as_of_date is None or as_of_date == "":
        return date.today()
    if isinstance(as_of_date, date):
        return as_of_date
    text = str(as_of_date).strip()
    return date.fromisoformat(text[:10])


def _parse_severe_plant_threshold(value: int | str | None) -> int:
    if value is None or value == "":
        return WHITE_MOTH_SEVERE_PLANT_THRESHOLD
    try:
        threshold = int(value)
    except (TypeError, ValueError) as exc:
        raise ValueError("严重点位阈值必须是整数") from exc
    if threshold < 1:
        raise ValueError("严重点位阈值必须 ≥ 1")
    if threshold > 10000:
        raise ValueError("严重点位阈值过大")
    return threshold
