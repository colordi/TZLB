from __future__ import annotations

from datetime import date
from typing import Any

from backend.db.postgres import ensure_pool


WHITE_MOTH_DAILY_COLUMNS: tuple[dict[str, str], ...] = (
    {"key": "date", "label": "日期", "type": "date"},
    {"key": "daily_treatment_plants", "label": "当日除治量（株）", "type": "number"},
    {"key": "cumulative_completed_points", "label": "累积防治完成点数", "type": "number"},
    {"key": "urban_daily_damaged_points", "label": "城区当日受害点位数", "type": "number"},
    {"key": "urban_daily_damaged_plants", "label": "城区当日受害株数", "type": "number"},
    {"key": "urban_daily_inspected_points", "label": "城区当日巡查点位数", "type": "number"},
    {"key": "town_daily_damaged_plants", "label": "乡镇当日受害株数", "type": "number"},
    {"key": "town_daily_damaged_points", "label": "乡镇当日受害点位数", "type": "number"},
    {"key": "town_daily_inspected_points", "label": "乡镇当日巡查点位数", "type": "number"},
    {"key": "daily_dispatch_points", "label": "当日派单数", "type": "number"},
)

WHITE_MOTH_DAILY_SQL = """
WITH ledger_dates AS (
    SELECT
        to_date(btrim(date_text), 'YYYY/MM/DD') AS "日期"
    FROM
        ledger."美国白蛾问题点位台账" l
        CROSS JOIN LATERAL regexp_split_to_table(
            concat_ws(
                '、',
                NULLIF(l."调查日期列表", ''),
                NULLIF(l."防治日期列表", '')
            ),
            '、'
        ) AS date_text
    WHERE
        btrim(date_text) <> ''
        AND ($1::integer IS NULL OR l."年份" = $1::integer)
        AND ($2::text IS NULL OR l."世代" = $2::text)
),

dates AS (
    SELECT
        "调查日期" AS "日期"
    FROM
        survey."美国白蛾调查表"
    WHERE
        ($1::integer IS NULL OR "年份" = $1::integer)
        AND ($2::text IS NULL OR "世代" = $2::text)

    UNION

    SELECT
        "日期"
    FROM
        ledger_dates
),

survey_daily AS (
    SELECT
        "调查日期" AS "日期",

        COALESCE(SUM(COALESCE("受害株数", 0)) FILTER (
            WHERE "是否剪网" = '是'
        ), 0) :: INTEGER AS "当日除治量（株）",

        COUNT(*) FILTER (
            WHERE COALESCE("区域", '乡镇') = '城区'
              AND COALESCE("受害株数", 0) > 0
        ) :: INTEGER AS "城区当日受害点位数",

        COALESCE(SUM(COALESCE("受害株数", 0)) FILTER (
            WHERE COALESCE("区域", '乡镇') = '城区'
        ), 0) :: INTEGER AS "城区当日受害株数",

        COUNT(*) FILTER (
            WHERE COALESCE("区域", '乡镇') = '城区'
        ) :: INTEGER AS "城区当日巡查点位数",

        COALESCE(SUM(COALESCE("受害株数", 0)) FILTER (
            WHERE COALESCE("区域", '乡镇') = '乡镇'
        ), 0) :: INTEGER AS "乡镇当日受害株数",

        COUNT(*) FILTER (
            WHERE COALESCE("区域", '乡镇') = '乡镇'
              AND COALESCE("受害株数", 0) > 0
        ) :: INTEGER AS "乡镇当日受害点位数",

        COUNT(*) FILTER (
            WHERE COALESCE("区域", '乡镇') = '乡镇'
        ) :: INTEGER AS "乡镇当日巡查点位数",

        COUNT(*) FILTER (
            WHERE COALESCE("受害株数", 0) > 0
        ) :: INTEGER AS "当日派单数"
    FROM
        survey."美国白蛾调查表"
    WHERE
        ($1::integer IS NULL OR "年份" = $1::integer)
        AND ($2::text IS NULL OR "世代" = $2::text)
    GROUP BY
        "调查日期"
),

ledger_completed AS (
    SELECT
        l."编号",
        CASE
            WHEN l."剪网彻底" = '是'
                THEN survey_dates.first_survey_date

            WHEN COALESCE(l."防治次数", 0) <> 0
             AND l."剪网彻底" IS DISTINCT FROM '是'
                THEN treatment_dates.first_treatment_date
        END AS "完成日期"
    FROM
        ledger."美国白蛾问题点位台账" l
        LEFT JOIN LATERAL (
            SELECT
                MIN(to_date(btrim(date_text), 'YYYY/MM/DD')) AS first_survey_date
            FROM
                regexp_split_to_table(l."调查日期列表", '、') AS date_text
            WHERE
                btrim(date_text) <> ''
        ) survey_dates ON TRUE
        LEFT JOIN LATERAL (
            SELECT
                MIN(to_date(btrim(date_text), 'YYYY/MM/DD')) AS first_treatment_date
            FROM
                regexp_split_to_table(l."防治日期列表", '、') AS date_text
            WHERE
                btrim(date_text) <> ''
        ) treatment_dates ON TRUE
    WHERE
        (
            l."剪网彻底" = '是'
            OR (
                COALESCE(l."防治次数", 0) <> 0
                AND l."剪网彻底" IS DISTINCT FROM '是'
            )
        )
        AND ($1::integer IS NULL OR l."年份" = $1::integer)
        AND ($2::text IS NULL OR l."世代" = $2::text)
),

completed_daily AS (
    SELECT
        d."日期",
        COUNT(lc."编号") :: INTEGER AS "累积防治完成点数"
    FROM
        dates d
        LEFT JOIN ledger_completed lc
            ON lc."完成日期" <= d."日期"
    GROUP BY
        d."日期"
)

SELECT
    d."日期",
    COALESCE(sd."当日除治量（株）", 0) :: INTEGER AS "当日除治量（株）",
    COALESCE(cd."累积防治完成点数", 0) :: INTEGER AS "累积防治完成点数",
    COALESCE(sd."城区当日受害点位数", 0) :: INTEGER AS "城区当日受害点位数",
    COALESCE(sd."城区当日受害株数", 0) :: INTEGER AS "城区当日受害株数",
    COALESCE(sd."城区当日巡查点位数", 0) :: INTEGER AS "城区当日巡查点位数",
    COALESCE(sd."乡镇当日受害株数", 0) :: INTEGER AS "乡镇当日受害株数",
    COALESCE(sd."乡镇当日受害点位数", 0) :: INTEGER AS "乡镇当日受害点位数",
    COALESCE(sd."乡镇当日巡查点位数", 0) :: INTEGER AS "乡镇当日巡查点位数",
    COALESCE(sd."当日派单数", 0) :: INTEGER AS "当日派单数"
FROM
    dates d
    LEFT JOIN survey_daily sd
        ON sd."日期" = d."日期"
    LEFT JOIN completed_daily cd
        ON cd."日期" = d."日期"
ORDER BY
    d."日期" DESC;
"""

WHITE_MOTH_ROW_FIELD_MAP: tuple[tuple[str, str], ...] = (
    ("date", "日期"),
    ("daily_treatment_plants", "当日除治量（株）"),
    ("cumulative_completed_points", "累积防治完成点数"),
    ("urban_daily_damaged_points", "城区当日受害点位数"),
    ("urban_daily_damaged_plants", "城区当日受害株数"),
    ("urban_daily_inspected_points", "城区当日巡查点位数"),
    ("town_daily_damaged_plants", "乡镇当日受害株数"),
    ("town_daily_damaged_points", "乡镇当日受害点位数"),
    ("town_daily_inspected_points", "乡镇当日巡查点位数"),
    ("daily_dispatch_points", "当日派单数"),
)

WHITE_MOTH_GENERATION_SUMMARY_SQL = """
WITH generations("世代", sort_order) AS (
    VALUES ('第一代'::text, 1), ('第二代'::text, 2), ('第三代'::text, 3)
),
point_stats AS (
    SELECT
        "世代",
        BTRIM("编号") AS "编号",
        CASE
            WHEN BOOL_OR(COALESCE("区域", '乡镇') = '城区') THEN '城区'
            ELSE '乡镇'
        END AS "区域",
        COUNT(*) FILTER (WHERE COALESCE("受害株数", 0) > 0)::integer AS dispatch_count
    FROM survey."美国白蛾调查表"
    WHERE
        "年份" = EXTRACT(YEAR FROM CURRENT_DATE)::integer
        AND "调查日期" <= CURRENT_DATE
        AND BTRIM(COALESCE("编号", '')) <> ''
    GROUP BY "世代", BTRIM("编号")
),
generation_stats AS (
    SELECT
        "世代",
        COUNT(*)::integer AS surveyed_points,
        COUNT(*) FILTER (WHERE "区域" = '城区')::integer AS urban_surveyed_points,
        COUNT(*) FILTER (WHERE "区域" = '乡镇')::integer AS town_surveyed_points,
        COUNT(*) FILTER (WHERE dispatch_count > 0)::integer AS damaged_points,
        COUNT(*) FILTER (WHERE dispatch_count > 0 AND "区域" = '城区')::integer AS urban_damaged_points,
        COUNT(*) FILTER (WHERE dispatch_count > 0 AND "区域" = '乡镇')::integer AS town_damaged_points,
        COALESCE(SUM(dispatch_count), 0)::integer AS dispatch_count
    FROM point_stats
    GROUP BY "世代"
)
SELECT
    CURRENT_DATE AS as_of_date,
    EXTRACT(YEAR FROM CURRENT_DATE)::integer AS year,
    g."世代",
    COALESCE(s.surveyed_points, 0)::integer AS surveyed_points,
    COALESCE(s.urban_surveyed_points, 0)::integer AS urban_surveyed_points,
    COALESCE(s.town_surveyed_points, 0)::integer AS town_surveyed_points,
    COALESCE(s.damaged_points, 0)::integer AS damaged_points,
    COALESCE(s.urban_damaged_points, 0)::integer AS urban_damaged_points,
    COALESCE(s.town_damaged_points, 0)::integer AS town_damaged_points,
    COALESCE(s.dispatch_count, 0)::integer AS dispatch_count
FROM generations g
LEFT JOIN generation_stats s ON s."世代" = g."世代"
ORDER BY g.sort_order;
"""

WHITE_MOTH_DISPATCH_FREQUENCY_SQL = """
WITH point_dispatch AS (
    SELECT
        "世代",
        BTRIM("编号") AS "编号",
        COUNT(*) FILTER (WHERE COALESCE("受害株数", 0) > 0)::integer AS dispatch_times
    FROM survey."美国白蛾调查表"
    WHERE
        "年份" = EXTRACT(YEAR FROM CURRENT_DATE)::integer
        AND "调查日期" <= CURRENT_DATE
        AND BTRIM(COALESCE("编号", '')) <> ''
    GROUP BY "世代", BTRIM("编号")
)
SELECT
    "世代",
    dispatch_times,
    COUNT(*)::integer AS point_count
FROM point_dispatch
WHERE dispatch_times > 0
GROUP BY "世代", dispatch_times
ORDER BY "世代", dispatch_times;
"""


def serialize_daily_value(value: Any) -> Any:
    if isinstance(value, date):
        return value.isoformat()
    return value


def serialize_white_moth_daily_row(row: Any) -> dict[str, Any]:
    return {
        public_key: serialize_daily_value(row[chinese_key])
        for public_key, chinese_key in WHITE_MOTH_ROW_FIELD_MAP
    }


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


async def get_white_moth_generation_summary() -> dict[str, Any]:
    pool = await ensure_pool()
    async with pool.acquire() as connection:
        summary_rows = await connection.fetch(WHITE_MOTH_GENERATION_SUMMARY_SQL)
        frequency_rows = await connection.fetch(WHITE_MOTH_DISPATCH_FREQUENCY_SQL)

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
        "year": summary_rows[0]["year"] if summary_rows else date.today().year,
        "generations": generations,
    }
