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
from backend.services.statistics.sql_other_pest import (
    OTHER_PEST_PEST_TYPE_SQL,
    OTHER_PEST_STATUS_SQL,
    OTHER_PEST_TOTALS_SQL,
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


async def get_other_pest_summary(year: int | None = None) -> dict[str, Any]:
    effective_year = year or date.today().year
    pool = await ensure_pool()
    async with pool.acquire() as connection:
        totals_rows = await connection.fetch(OTHER_PEST_TOTALS_SQL, effective_year)
        status_rows = await connection.fetch(OTHER_PEST_STATUS_SQL, effective_year)
        pest_type_rows = await connection.fetch(OTHER_PEST_PEST_TYPE_SQL, effective_year)

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
