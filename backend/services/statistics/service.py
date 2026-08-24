from __future__ import annotations

from datetime import date
from typing import Any

from backend.db.postgres import ensure_pool
from backend.services.statistics.serializers import (
    _completion_rate,
    _parse_as_of_date,
    _parse_severe_plant_threshold,
    merge_locality_summary_rows,
    serialize_daily_value,
    serialize_white_moth_daily_row,
)
from backend.services.statistics.sql_daily import (
    WHITE_MOTH_DAILY_COLUMNS,
    WHITE_MOTH_DAILY_SQL,
)
from backend.services.statistics.sql_generation import (
    WHITE_MOTH_DISPATCH_FREQUENCY_SQL,
    WHITE_MOTH_GENERATION_SUMMARY_SQL,
)
from backend.services.statistics.host_summary import (
    aggregate_host_summary,
    aggregate_host_summary_by_generation,
)
from backend.services.statistics.sql_host import (
    WHITE_MOTH_HOST_RAW_SQL,
)
from backend.services.statistics.sql_locality import (
    WHITE_MOTH_LOCALITY_SEVERE_SITES_SQL,
    WHITE_MOTH_LOCALITY_SUMMARY_SQL,
)
from backend.services.statistics.sql_ash_borer import (
    ASH_BORER_LOCALITY_SQL,
    ASH_BORER_TOTALS_SQL,
    ASH_BORER_TREES_PER_POINT,
)
from backend.services.statistics.sql_other_pest import (
    OTHER_PEST_PEST_TYPE_SQL,
    OTHER_PEST_STATUS_SQL,
    OTHER_PEST_TOTALS_SQL,
)
from backend.services.statistics.sql_sophora import (
    SOPHORA_GENERATION_SUMMARY_SQL,
    SOPHORA_LOCALITY_ORDER,
    SOPHORA_LOCALITY_SEVERE_SITES_SQL,
    SOPHORA_LOCALITY_SUMMARY_SQL,
)
from backend.services.statistics.sql_spring_inchworm import (
    SPRING_INCHWORM_ADULT_DAMAGE_LEVEL_SQL,
    SPRING_INCHWORM_ADULT_TOTALS_SQL,
    SPRING_INCHWORM_LARVA_DAMAGE_LEVEL_SQL,
    SPRING_INCHWORM_LARVA_TOTALS_SQL,
    SPRING_INCHWORM_RING_TOTALS_SQL,
    SPRING_INCHWORM_STATUS_SQL,
)
from backend.services.statistics.sql_yangshu_shiye import (
    YANGSHU_SHIYE_PEST_TYPE_SQL,
    YANGSHU_SHIYE_STATUS_SQL,
    YANGSHU_SHIYE_TOTALS_SQL,
)
from backend.services.statistics.sql_years import (
    STATISTICS_MODULE_KEYS,
    STATISTICS_YEARS_SQL,
)


async def get_white_moth_daily_statistics(
    year: int | None = None,
    generation: str | None = None,
) -> dict[str, Any]:
    pool = await ensure_pool()
    async with pool.acquire() as connection:
        rows = await connection.fetch(WHITE_MOTH_DAILY_SQL, year, generation)

    return {
        "columns": list(WHITE_MOTH_DAILY_COLUMNS),
        "rows": [serialize_white_moth_daily_row(row) for row in rows],
    }


async def get_white_moth_generation_summary(year: int | None = None) -> dict[str, Any]:
    effective_year = year or date.today().year
    pool = await ensure_pool()
    async with pool.acquire() as connection:
        summary_rows = await connection.fetch(WHITE_MOTH_GENERATION_SUMMARY_SQL, effective_year)
        frequency_rows = await connection.fetch(WHITE_MOTH_DISPATCH_FREQUENCY_SQL, effective_year)

    frequencies: dict[str, list[dict[str, int]]] = {}
    for row in frequency_rows:
        frequencies.setdefault(row["世代"], []).append(
            {
                "dispatch_times": row["dispatch_times"],
                "point_count": row["point_count"],
            }
        )

    generations = [
        {
            "generation": row["世代"],
            "start_date": serialize_daily_value(row["start_date"]),
            "end_date": serialize_daily_value(row["end_date"]),
            "surveyed_points": row["surveyed_points"],
            "urban_surveyed_points": row["urban_surveyed_points"],
            "town_surveyed_points": row["town_surveyed_points"],
            "damaged_points": row["damaged_points"],
            "urban_damaged_points": row["urban_damaged_points"],
            "town_damaged_points": row["town_damaged_points"],
            "dispatch_count": row["dispatch_count"],
            "dispatch_frequency": frequencies.get(row["世代"], []),
        }
        for row in summary_rows
    ]

    return {
        "as_of_date": serialize_daily_value(summary_rows[0]["as_of_date"]) if summary_rows else None,
        "year": summary_rows[0]["year"] if summary_rows else effective_year,
        "generations": generations,
    }

async def get_white_moth_locality_summary(
    year: int | None = None,
    generation: str | None = None,
    as_of_date: date | str | None = None,
    severe_plant_threshold: int | str | None = None,
) -> dict[str, Any]:
    effective_year = year or date.today().year
    effective_as_of = _parse_as_of_date(as_of_date)
    effective_threshold = _parse_severe_plant_threshold(severe_plant_threshold)
    pool = await ensure_pool()
    async with pool.acquire() as connection:
        rows = await connection.fetch(
            WHITE_MOTH_LOCALITY_SUMMARY_SQL,
            effective_year,
            generation,
            effective_threshold,
            effective_as_of,
        )
        severe_site_rows = await connection.fetch(
            WHITE_MOTH_LOCALITY_SEVERE_SITES_SQL,
            effective_year,
            generation,
            effective_threshold,
            effective_as_of,
        )

    localities = merge_locality_summary_rows(rows, severe_site_rows)
    damaged_points = sum(item["damaged_points"] for item in localities)
    completed_points = sum(item["completed_points"] for item in localities)
    totals = {
        "damaged_points": damaged_points,
        "damaged_plants": sum(item["damaged_plants"] for item in localities),
        "completed_points": completed_points,
        "completion_rate": _completion_rate(completed_points, damaged_points),
        "severe_points": sum(item["severe_points"] for item in localities),
        "collab_points": sum(item["collab_points"] for item in localities),
    }

    return {
        "year": effective_year,
        "generation": generation,
        "as_of_date": serialize_daily_value(effective_as_of),
        "severe_plant_threshold": effective_threshold,
        "totals": totals,
        "localities": localities,
    }


async def get_white_moth_host_summary(
    year: int | None = None,
    generation: str | None = None,
    by_generation: bool = False,
) -> dict[str, Any]:
    effective_year = year or date.today().year
    pool = await ensure_pool()
    async with pool.acquire() as connection:
        rows = await connection.fetch(WHITE_MOTH_HOST_RAW_SQL, effective_year, generation)

    if by_generation and not generation:
        return {
            "year": effective_year,
            "generation": None,
            "generations": aggregate_host_summary_by_generation(rows),
        }

    summary = aggregate_host_summary(rows)
    return {
        "year": effective_year,
        "generation": generation,
        **summary,
    }


def _rate(numerator: int, denominator: int) -> float | None:
    if denominator <= 0:
        return None
    return round(numerator / denominator * 100, 1)


def _avg_insect(value: Any) -> float | None:
    if value is None:
        return None
    return round(float(value), 1)


def _serialize_sophora_generation_row(row: Any) -> dict[str, Any]:
    surveyed = int(row["surveyed_points"] or 0)
    damaged = int(row["damaged_points"] or 0)
    ledger_points = int(row["ledger_points"] or 0)
    closed = int(row["closed_points"] or 0)
    return {
        "generation": row["世代"],
        "start_date": serialize_daily_value(row["start_date"]),
        "end_date": serialize_daily_value(row["end_date"]),
        "surveyed_points": surveyed,
        "damaged_points": damaged,
        "damage_rate": _rate(damaged, surveyed),
        "light_points": int(row["light_points"] or 0),
        "medium_points": int(row["medium_points"] or 0),
        "severe_points": int(row["severe_points"] or 0),
        "avg_insect_count": _avg_insect(row["avg_insect_count"]),
        "ledger_points": ledger_points,
        "pending_treatment": int(row["pending_treatment"] or 0),
        "pending_recheck": int(row["pending_recheck"] or 0),
        "recheck_abnormal": int(row["recheck_abnormal"] or 0),
        "closed_points": closed,
        "closure_rate": _rate(closed, ledger_points),
    }


def _serialize_sophora_locality_row(row: Any) -> dict[str, Any]:
    monitor = int(row["monitor_points"] or 0)
    surveyed = int(row["surveyed_points"] or 0)
    damaged = int(row["damaged_points"] or 0)
    ledger_points = int(row["ledger_points"] or 0)
    closed = int(row["closed_points"] or 0)
    return {
        "locality": row["locality"],
        "monitor_points": monitor,
        "surveyed_points": surveyed,
        "coverage_rate": _rate(surveyed, monitor),
        "damaged_points": damaged,
        "light_points": int(row["light_points"] or 0),
        "medium_points": int(row["medium_points"] or 0),
        "severe_points": int(row["severe_points"] or 0),
        "avg_insect_count": _avg_insect(row["avg_insect_count"]),
        "ledger_points": ledger_points,
        "pending_treatment": int(row["pending_treatment"] or 0),
        "pending_recheck": int(row["pending_recheck"] or 0),
        "recheck_abnormal": int(row["recheck_abnormal"] or 0),
        "closed_points": closed,
        "closure_rate": _rate(closed, ledger_points),
        "severe_sites": [],
    }


def _serialize_sophora_severe_site(row: Any) -> dict[str, Any]:
    return {
        "code": row["code"] or "",
        "name": row["name"] or "--",
        "avg_insect_count": int(row["avg_insect_count"] or 0),
        "survey_date": serialize_daily_value(row["survey_date"]),
        "ledger_status": row["ledger_status"] or None,
    }


def _merge_sophora_localities(
    rows: list[Any],
    severe_site_rows: list[Any] | None = None,
) -> list[dict[str, Any]]:
    by_locality = {
        item["locality"]: item
        for item in (_serialize_sophora_locality_row(row) for row in rows)
    }
    empty = {
        "monitor_points": 0,
        "surveyed_points": 0,
        "coverage_rate": None,
        "damaged_points": 0,
        "light_points": 0,
        "medium_points": 0,
        "severe_points": 0,
        "avg_insect_count": None,
        "ledger_points": 0,
        "pending_treatment": 0,
        "pending_recheck": 0,
        "recheck_abnormal": 0,
        "closed_points": 0,
        "closure_rate": None,
        "severe_sites": [],
    }

    severe_by_locality: dict[str, list[dict[str, Any]]] = {}
    for row in severe_site_rows or []:
        locality = row["locality"]
        severe_by_locality.setdefault(locality, []).append(
            _serialize_sophora_severe_site(row)
        )

    localities: list[dict[str, Any]] = []
    seen: set[str] = set()
    for locality in SOPHORA_LOCALITY_ORDER:
        seen.add(locality)
        item = {"locality": locality, **by_locality.get(locality, empty)}
        sites = severe_by_locality.get(locality, [])
        item["severe_sites"] = sites
        item["severe_points"] = len(sites) if sites else int(item.get("severe_points") or 0)
        localities.append(item)

    # 清单外属地（理论上已归一到「其他单位」）兜底追加
    for locality, item in by_locality.items():
        if locality in seen:
            continue
        sites = severe_by_locality.get(locality, [])
        item = {**item, "severe_sites": sites}
        item["severe_points"] = len(sites) if sites else int(item.get("severe_points") or 0)
        localities.append(item)

    return localities


async def get_sophora_generation_summary(year: int | None = None) -> dict[str, Any]:
    effective_year = year or date.today().year
    pool = await ensure_pool()
    async with pool.acquire() as connection:
        rows = await connection.fetch(SOPHORA_GENERATION_SUMMARY_SQL, effective_year)

    generations = [_serialize_sophora_generation_row(row) for row in rows]
    return {
        "as_of_date": serialize_daily_value(rows[0]["as_of_date"]) if rows else None,
        "year": rows[0]["year"] if rows else effective_year,
        "generations": generations,
    }


async def get_sophora_locality_summary(
    year: int | None = None,
    generation: str | None = None,
) -> dict[str, Any]:
    effective_year = year or date.today().year
    effective_generation = (generation or "").strip() or None
    pool = await ensure_pool()
    async with pool.acquire() as connection:
        rows = await connection.fetch(
            SOPHORA_LOCALITY_SUMMARY_SQL,
            effective_year,
            effective_generation,
        )
        severe_site_rows = await connection.fetch(
            SOPHORA_LOCALITY_SEVERE_SITES_SQL,
            effective_year,
            effective_generation,
        )

    localities = _merge_sophora_localities(rows, severe_site_rows)
    surveyed_points = sum(item["surveyed_points"] for item in localities)
    damaged_points = sum(item["damaged_points"] for item in localities)
    ledger_points = sum(item["ledger_points"] for item in localities)
    closed_points = sum(item["closed_points"] for item in localities)
    totals = {
        "surveyed_points": surveyed_points,
        "damaged_points": damaged_points,
        "damage_rate": _rate(damaged_points, surveyed_points),
        "severe_points": sum(item["severe_points"] for item in localities),
        "ledger_points": ledger_points,
        "closed_points": closed_points,
        "closure_rate": _rate(closed_points, ledger_points),
    }

    return {
        "year": effective_year,
        "generation": effective_generation,
        "totals": totals,
        "localities": localities,
    }


def _assemble_survey_ledger_summary(
    effective_year: int,
    totals_rows: list[Any],
    status_rows: list[Any],
    pest_type_rows: list[Any],
) -> dict[str, Any]:
    """组装「调查表 + 台账」型整体汇总（其他害虫、杨树食叶害虫共用）。"""

    totals_row = totals_rows[0] if totals_rows else {}
    survey_records = int(totals_row.get("survey_records") or 0)
    problem_records = int(totals_row.get("problem_records") or 0)
    status_counts = [
        {"status": row["status"] or "未知", "count": int(row["count"] or 0)}
        for row in status_rows
    ]

    return {
        "year": effective_year,
        "totals": {
            "survey_records": survey_records,
            "surveyed_points": int(totals_row.get("surveyed_points") or 0),
            "problem_records": problem_records,
            "no_problem_records": survey_records - problem_records,
            "problem_points": int(totals_row.get("problem_points") or 0),
            "problem_rate": _completion_rate(problem_records, survey_records),
            "last_survey_date": serialize_daily_value(totals_row.get("last_survey_date")),
            "ledger_points": sum(item["count"] for item in status_counts),
            "status_counts": status_counts,
        },
        "pest_types": [
            {
                "pest_type": row["pest_type"] or "未知",
                "survey_records": int(row["survey_records"] or 0),
                "problem_records": int(row["problem_records"] or 0),
                "problem_points": int(row["problem_points"] or 0),
                "last_survey_date": serialize_daily_value(row["last_survey_date"]),
            }
            for row in pest_type_rows
        ],
    }


async def get_other_pest_summary(year: int | None = None) -> dict[str, Any]:
    effective_year = year or date.today().year
    pool = await ensure_pool()
    async with pool.acquire() as connection:
        totals_rows = await connection.fetch(OTHER_PEST_TOTALS_SQL, effective_year)
        status_rows = await connection.fetch(OTHER_PEST_STATUS_SQL, effective_year)
        pest_type_rows = await connection.fetch(OTHER_PEST_PEST_TYPE_SQL, effective_year)

    return _assemble_survey_ledger_summary(
        effective_year, totals_rows, status_rows, pest_type_rows
    )


async def get_yangshu_shiye_summary(year: int | None = None) -> dict[str, Any]:
    effective_year = year or date.today().year
    pool = await ensure_pool()
    async with pool.acquire() as connection:
        totals_rows = await connection.fetch(YANGSHU_SHIYE_TOTALS_SQL, effective_year)
        status_rows = await connection.fetch(YANGSHU_SHIYE_STATUS_SQL, effective_year)
        pest_type_rows = await connection.fetch(YANGSHU_SHIYE_PEST_TYPE_SQL, effective_year)

    return _assemble_survey_ledger_summary(
        effective_year, totals_rows, status_rows, pest_type_rows
    )


ASH_BORER_DAMAGE_LEVEL_KEYS = ("none", "light", "medium", "high")
ASH_BORER_DAMAGE_LEVEL_THRESHOLDS = {
    "none": 0,
    "light": 10,
    "medium": 20,
}


def _serialize_ash_borer_damage_levels(row: Any, prefix: str) -> dict[str, int]:
    return {
        key: int(row.get(f"{prefix}_{key}") or 0) for key in ASH_BORER_DAMAGE_LEVEL_KEYS
    }


def _serialize_ash_borer_counts(row: Any) -> dict[str, Any]:
    """序列化白蜡蛀干害虫合计：率值分母为有效点位数 × 每点位 30 株。"""

    points = int(row.get("surveyed_points") or 0)
    dead_plants = int(row.get("dead_plants") or 0)
    felled_plants = int(row.get("felled_plants") or 0)
    agrilus_damaged_plants = int(row.get("agrilus_damaged_plants") or 0)
    cossus_damaged_plants = int(row.get("cossus_damaged_plants") or 0)
    surveyed_trees = points * ASH_BORER_TREES_PER_POINT
    return {
        "survey_records": int(row.get("survey_records") or 0),
        "surveyed_points": points,
        "surveyed_trees": surveyed_trees,
        "excluded_points": int(row.get("excluded_points") or 0),
        "agrilus_damaged_plants": agrilus_damaged_plants,
        "cossus_damaged_plants": cossus_damaged_plants,
        "dead_plants": dead_plants,
        "felled_plants": felled_plants,
        "mortality_rate": _rate(dead_plants + felled_plants, surveyed_trees),
        "agrilus_infestation_rate": _rate(agrilus_damaged_plants, surveyed_trees),
        "cossus_infestation_rate": _rate(cossus_damaged_plants, surveyed_trees),
        "agrilus_damage_levels": _serialize_ash_borer_damage_levels(row, "agrilus"),
        "cossus_damage_levels": _serialize_ash_borer_damage_levels(row, "cossus"),
        "last_survey_date": serialize_daily_value(row.get("last_survey_date")),
    }


async def get_ash_borer_summary(year: int | None = None) -> dict[str, Any]:
    effective_year = year or date.today().year
    pool = await ensure_pool()
    async with pool.acquire() as connection:
        totals_rows = await connection.fetch(ASH_BORER_TOTALS_SQL, effective_year)
        locality_rows = await connection.fetch(ASH_BORER_LOCALITY_SQL, effective_year)

    totals_row = totals_rows[0] if totals_rows else {}
    totals = _serialize_ash_borer_counts(totals_row)
    totals["agrilus_holes"] = int(totals_row.get("agrilus_holes") or 0)

    return {
        "year": effective_year,
        "trees_per_point": ASH_BORER_TREES_PER_POINT,
        "damage_level_thresholds": dict(ASH_BORER_DAMAGE_LEVEL_THRESHOLDS),
        "totals": totals,
        "localities": [
            {"locality": row["locality"] or "未知", **_serialize_ash_borer_counts(row)}
            for row in locality_rows
        ],
    }


def _serialize_insect_survey_totals(
    row: Any,
    damage_level_rows: list[Any],
) -> dict[str, Any]:
    return {
        "survey_records": int(row.get("survey_records") or 0),
        "surveyed_points": int(row.get("surveyed_points") or 0),
        "avg_insect_count": _avg_insect(row.get("avg_insect_count")),
        "total_insect_count": int(row.get("total_insect_count") or 0),
        "last_survey_date": serialize_daily_value(row.get("last_survey_date")),
        "damage_levels": [
            {"damage_level": item["damage_level"] or "未知", "count": int(item["count"] or 0)}
            for item in damage_level_rows
        ],
    }


async def get_spring_inchworm_summary(year: int | None = None) -> dict[str, Any]:
    effective_year = year or date.today().year
    pool = await ensure_pool()
    async with pool.acquire() as connection:
        adult_totals_rows = await connection.fetch(
            SPRING_INCHWORM_ADULT_TOTALS_SQL, effective_year
        )
        adult_level_rows = await connection.fetch(
            SPRING_INCHWORM_ADULT_DAMAGE_LEVEL_SQL, effective_year
        )
        larva_totals_rows = await connection.fetch(
            SPRING_INCHWORM_LARVA_TOTALS_SQL, effective_year
        )
        larva_level_rows = await connection.fetch(
            SPRING_INCHWORM_LARVA_DAMAGE_LEVEL_SQL, effective_year
        )
        ring_totals_rows = await connection.fetch(
            SPRING_INCHWORM_RING_TOTALS_SQL, effective_year
        )
        status_rows = await connection.fetch(SPRING_INCHWORM_STATUS_SQL, effective_year)

    ring_row = ring_totals_rows[0] if ring_totals_rows else {}
    status_counts = [
        {"status": row["status"] or "未知", "count": int(row["count"] or 0)}
        for row in status_rows
    ]

    return {
        "year": effective_year,
        "adult": _serialize_insect_survey_totals(
            adult_totals_rows[0] if adult_totals_rows else {}, adult_level_rows
        ),
        "larva": _serialize_insect_survey_totals(
            larva_totals_rows[0] if larva_totals_rows else {}, larva_level_rows
        ),
        "ring_wrap": {
            "survey_records": int(ring_row.get("survey_records") or 0),
            "surveyed_points": int(ring_row.get("surveyed_points") or 0),
            "repair_count": int(ring_row.get("repair_count") or 0),
            "adult_count": int(ring_row.get("adult_count") or 0),
            "last_survey_date": serialize_daily_value(ring_row.get("last_survey_date")),
        },
        "ledger": {
            "ledger_points": sum(item["count"] for item in status_counts),
            "status_counts": status_counts,
        },
    }


async def get_statistics_years() -> dict[str, list[int]]:
    """各统计模块的实际数据年份（升序），无数据的模块返回空列表。"""

    pool = await ensure_pool()
    async with pool.acquire() as connection:
        rows = await connection.fetch(STATISTICS_YEARS_SQL)

    years_by_module: dict[str, list[int]] = {key: [] for key in STATISTICS_MODULE_KEYS}
    for row in rows:
        module = row["module"]
        if module in years_by_module:
            years_by_module[module].append(int(row["year"]))
    return years_by_module
