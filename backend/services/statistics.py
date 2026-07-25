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

-- 同年同世代同点位只认首次受害记录（对齐台账「一点一行 / 首次下派」口径）
first_damage AS (
    SELECT DISTINCT ON (
        "年份",
        "世代",
        BTRIM("编号")
    )
        "调查日期" AS "日期",
        COALESCE("区域", '乡镇') AS "区域",
        COALESCE("受害株数", 0) AS "受害株数"
    FROM
        survey."美国白蛾调查表"
    WHERE
        BTRIM(COALESCE("编号", '')) <> ''
        AND COALESCE("受害株数", 0) > 0
        AND ($1::integer IS NULL OR "年份" = $1::integer)
        AND ($2::text IS NULL OR "世代" = $2::text)
    ORDER BY
        "年份",
        "世代",
        BTRIM("编号"),
        "调查日期"
),

first_damage_daily AS (
    SELECT
        "日期",
        COUNT(*) FILTER (
            WHERE "区域" = '城区'
        ) :: INTEGER AS "城区当日受害点位数",
        COALESCE(SUM("受害株数") FILTER (
            WHERE "区域" = '城区'
        ), 0) :: INTEGER AS "城区当日受害株数",
        COUNT(*) FILTER (
            WHERE "区域" = '乡镇'
        ) :: INTEGER AS "乡镇当日受害点位数",
        COALESCE(SUM("受害株数") FILTER (
            WHERE "区域" = '乡镇'
        ), 0) :: INTEGER AS "乡镇当日受害株数"
    FROM
        first_damage
    GROUP BY
        "日期"
),

-- 巡查含无受害；派单按当日全部受害行计（含复查）；除治量仍按当日调查行汇总
survey_daily AS (
    SELECT
        "调查日期" AS "日期",

        COALESCE(SUM(COALESCE("受害株数", 0)) FILTER (
            WHERE "是否剪网" = '是'
        ), 0) :: INTEGER AS "当日除治量（株）",

        COUNT(*) FILTER (
            WHERE COALESCE("区域", '乡镇') = '城区'
        ) :: INTEGER AS "城区当日巡查点位数",

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
    COALESCE(fd."城区当日受害点位数", 0) :: INTEGER AS "城区当日受害点位数",
    COALESCE(fd."城区当日受害株数", 0) :: INTEGER AS "城区当日受害株数",
    COALESCE(sd."城区当日巡查点位数", 0) :: INTEGER AS "城区当日巡查点位数",
    COALESCE(fd."乡镇当日受害株数", 0) :: INTEGER AS "乡镇当日受害株数",
    COALESCE(fd."乡镇当日受害点位数", 0) :: INTEGER AS "乡镇当日受害点位数",
    COALESCE(sd."乡镇当日巡查点位数", 0) :: INTEGER AS "乡镇当日巡查点位数",
    COALESCE(sd."当日派单数", 0) :: INTEGER AS "当日派单数"
FROM
    dates d
    LEFT JOIN survey_daily sd
        ON sd."日期" = d."日期"
    LEFT JOIN first_damage_daily fd
        ON fd."日期" = d."日期"
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
first_survey AS (
    SELECT DISTINCT ON ("世代", BTRIM("编号"))
        "世代",
        BTRIM("编号") AS "编号",
        COALESCE("区域", '乡镇') AS "区域"
    FROM survey."美国白蛾调查表"
    WHERE
        "年份" = $1
        AND "调查日期" <= CURRENT_DATE
        AND BTRIM(COALESCE("编号", '')) <> ''
    ORDER BY "世代", BTRIM("编号"), "调查日期"
),
first_damage AS (
    SELECT DISTINCT ON ("世代", BTRIM("编号"))
        "世代",
        BTRIM("编号") AS "编号",
        COALESCE("区域", '乡镇') AS "区域"
    FROM survey."美国白蛾调查表"
    WHERE
        "年份" = $1
        AND "调查日期" <= CURRENT_DATE
        AND BTRIM(COALESCE("编号", '')) <> ''
        AND COALESCE("受害株数", 0) > 0
    ORDER BY "世代", BTRIM("编号"), "调查日期"
),
-- 派单次数按实际受害上报次数累计（含复查），与受害点位「只计首次」区分
point_dispatch AS (
    SELECT
        "世代",
        BTRIM("编号") AS "编号",
        COUNT(*) FILTER (WHERE COALESCE("受害株数", 0) > 0)::integer AS dispatch_count
    FROM survey."美国白蛾调查表"
    WHERE
        "年份" = $1
        AND "调查日期" <= CURRENT_DATE
        AND BTRIM(COALESCE("编号", '')) <> ''
    GROUP BY "世代", BTRIM("编号")
),
generation_stats AS (
    SELECT
        fs."世代",
        COUNT(*)::integer AS surveyed_points,
        COUNT(*) FILTER (WHERE fs."区域" = '城区')::integer AS urban_surveyed_points,
        COUNT(*) FILTER (WHERE fs."区域" = '乡镇')::integer AS town_surveyed_points,
        COUNT(fd."编号")::integer AS damaged_points,
        COUNT(fd."编号") FILTER (WHERE fd."区域" = '城区')::integer AS urban_damaged_points,
        COUNT(fd."编号") FILTER (WHERE fd."区域" = '乡镇')::integer AS town_damaged_points,
        COALESCE(SUM(pd.dispatch_count), 0)::integer AS dispatch_count
    FROM first_survey fs
    LEFT JOIN first_damage fd
        ON fd."世代" = fs."世代"
        AND fd."编号" = fs."编号"
    LEFT JOIN point_dispatch pd
        ON pd."世代" = fs."世代"
        AND pd."编号" = fs."编号"
    GROUP BY fs."世代"
),
generation_dates AS (
    SELECT
        "世代",
        MIN("调查日期") AS start_date,
        MAX("调查日期") AS end_date
    FROM survey."美国白蛾调查表"
    WHERE
        "年份" = $1
        AND "调查日期" <= CURRENT_DATE
    GROUP BY "世代"
)
SELECT
    CURRENT_DATE AS as_of_date,
    $1 AS year,
    g."世代",
    d.start_date,
    d.end_date,
    COALESCE(s.surveyed_points, 0)::integer AS surveyed_points,
    COALESCE(s.urban_surveyed_points, 0)::integer AS urban_surveyed_points,
    COALESCE(s.town_surveyed_points, 0)::integer AS town_surveyed_points,
    COALESCE(s.damaged_points, 0)::integer AS damaged_points,
    COALESCE(s.urban_damaged_points, 0)::integer AS urban_damaged_points,
    COALESCE(s.town_damaged_points, 0)::integer AS town_damaged_points,
    COALESCE(s.dispatch_count, 0)::integer AS dispatch_count
FROM generations g
LEFT JOIN generation_stats s ON s."世代" = g."世代"
LEFT JOIN generation_dates d ON d."世代" = g."世代"
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
        "年份" = $1
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

# 与《各属地受害清单》Excel 对齐；非清单属地归入「其他单位」
WHITE_MOTH_LOCALITY_ORDER: tuple[str, ...] = (
    "宋庄镇",
    "永顺镇",
    "梨园镇",
    "潞城镇",
    "台湖镇",
    "张家湾镇",
    "西集镇",
    "马驹桥镇",
    "漷县镇",
    "永乐店镇",
    "于家务乡",
    "新华街道",
    "北苑街道",
    "中仓街道",
    "玉桥街道",
    "通运街道",
    "潞邑街道",
    "临河里街道",
    "九棵树街道",
    "杨庄街道",
    "潞源街道",
    "文景街道",
    "其他单位",
)

WHITE_MOTH_CANONICAL_LOCALITIES: frozenset[str] = frozenset(
    locality for locality in WHITE_MOTH_LOCALITY_ORDER if locality != "其他单位"
)

# 受害株数汇总达到该阈值计为「严重点位」
WHITE_MOTH_SEVERE_PLANT_THRESHOLD = 10

_LOCALITY_CASE_SQL = "\n        ".join(
    f"WHEN BTRIM(COALESCE(\"属地\", '')) = '{locality}' THEN '{locality}'"
    for locality in WHITE_MOTH_CANONICAL_LOCALITIES
)

# $1 年份, $2 世代, $3 严重株数阈值, $4 截止日期（调查/下派截止）
# 纳入：首次调查日（无则首次下派日）<= 截止日 —— 圈定「截至该日已发现」的点位
# 完成：台账最新状态已完成（剪网彻底→有首次调查日；否则有防治→有首次防治日）
#       完成日不再与截止日比较，避免「先调查后防治」在截止调查日后完成的点被误判未完成
_LOCALITY_BASE_CTE = f"""
ledger_base AS (
    SELECT
        CASE
            {_LOCALITY_CASE_SQL}
            ELSE '其他单位'
        END AS locality,
        BTRIM(COALESCE(l."编号", '')) AS code,
        COALESCE(NULLIF(BTRIM(l."点位名称"), ''), '--') AS name,
        COALESCE(l."受害株数汇总", 0)::integer AS damaged_plants,
        POSITION('协同' IN COALESCE(l."备注", '')) > 0 AS is_collab,
        COALESCE(
            survey_dates.first_survey_date,
            dispatch_dates.first_dispatch_date
        ) AS first_known_date,
        CASE
            WHEN l."剪网彻底" = '是'
                THEN survey_dates.first_survey_date
            WHEN COALESCE(l."防治次数", 0) <> 0
             AND l."剪网彻底" IS DISTINCT FROM '是'
                THEN treatment_dates.first_treatment_date
        END AS completion_date
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
        LEFT JOIN LATERAL (
            SELECT
                MIN(to_date(btrim(date_text), 'YYYY/MM/DD')) AS first_dispatch_date
            FROM
                regexp_split_to_table(l."下派日期列表", '、') AS date_text
            WHERE
                btrim(date_text) <> ''
        ) dispatch_dates ON TRUE
    WHERE
        l."年份" = $1
        AND ($2::text IS NULL OR l."世代" = $2::text)
        AND COALESCE(
            survey_dates.first_survey_date,
            dispatch_dates.first_dispatch_date
        ) IS NOT NULL
        AND COALESCE(
            survey_dates.first_survey_date,
            dispatch_dates.first_dispatch_date
        ) <= $4::date
)
"""

WHITE_MOTH_LOCALITY_SUMMARY_SQL = f"""
WITH {_LOCALITY_BASE_CTE}
SELECT
    locality,
    COUNT(*)::integer AS damaged_points,
    COALESCE(SUM(damaged_plants), 0)::integer AS damaged_plants,
    COUNT(*) FILTER (
        WHERE completion_date IS NOT NULL
    )::integer AS completed_points,
    COUNT(*) FILTER (
        WHERE damaged_plants >= $3
    )::integer AS severe_points,
    COUNT(*) FILTER (
        WHERE is_collab
    )::integer AS collab_points
FROM
    ledger_base
GROUP BY
    locality
ORDER BY
    damaged_points DESC,
    locality;
"""

WHITE_MOTH_LOCALITY_SEVERE_SITES_SQL = f"""
WITH {_LOCALITY_BASE_CTE}
SELECT
    locality,
    code,
    name,
    damaged_plants
FROM
    ledger_base
WHERE
    damaged_plants >= $3
    AND code <> ''
ORDER BY
    locality,
    damaged_plants DESC,
    code;
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
        "collab_points": int(row["collab_points"] or 0),
        "severe_sites": [],
    }


def serialize_severe_site_row(row: Any) -> dict[str, Any]:
    return {
        "code": row["code"] or "",
        "name": row["name"] or "--",
        "damaged_plants": int(row["damaged_plants"] or 0),
    }


def merge_locality_summary_rows(
    rows: list[Any],
    severe_site_rows: list[Any] | None = None,
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
        "collab_points": 0,
        "severe_sites": [],
    }

    severe_by_locality: dict[str, list[dict[str, Any]]] = {}
    for row in severe_site_rows or []:
        locality = row["locality"]
        severe_by_locality.setdefault(locality, []).append(serialize_severe_site_row(row))

    localities: list[dict[str, Any]] = []
    for locality in WHITE_MOTH_LOCALITY_ORDER:
        item = {"locality": locality, **by_locality.get(locality, empty)}
        sites = severe_by_locality.get(locality, [])
        item["severe_sites"] = sites
        # 以名单长度为准，避免汇总与明细偶发不一致
        item["severe_points"] = len(sites) if sites else int(item.get("severe_points") or 0)
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
