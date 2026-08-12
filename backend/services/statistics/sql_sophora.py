"""国槐尺蠖统计 SQL。

口径（MVP）：
- 已调查点：同年同世代调查表去重编号
- 点位定级：同编号同年同世代取调查日期最新一条
- 受害：危害程度 ∈ {轻, 中, 重}（含轻）
- 严重：危害程度 = 重
- 台账状态：直接使用问题点位台账当前状态
"""

from __future__ import annotations

from backend.services.statistics.sql_locality import (
    WHITE_MOTH_CANONICAL_LOCALITIES,
    WHITE_MOTH_LOCALITY_ORDER,
)

SOPHORA_GENERATIONS: tuple[str, ...] = ("第一代", "第二代", "第三代")

# 复用白蛾属地清单与排序，保证全区统计展示一致
SOPHORA_LOCALITY_ORDER = WHITE_MOTH_LOCALITY_ORDER
SOPHORA_CANONICAL_LOCALITIES = WHITE_MOTH_CANONICAL_LOCALITIES


def _locality_case_sql(source_expr: str) -> str:
    """把任意属地表达式归一到清单属地，否则归入「其他单位」。"""

    branches = "\n            ".join(
        f"WHEN BTRIM(COALESCE({source_expr}, '')) = '{locality}' THEN '{locality}'"
        for locality in SOPHORA_CANONICAL_LOCALITIES
    )
    return f"""CASE
            {branches}
            ELSE '其他单位'
        END"""


_LOC_FROM_RAW = _locality_case_sql("loc_raw")
_LOC_FROM_SITE = _locality_case_sql('"属地"')

SOPHORA_GENERATION_SUMMARY_SQL = """
WITH generations("世代", sort_order) AS (
    VALUES
        ('第一代'::text, 1),
        ('第二代'::text, 2),
        ('第三代'::text, 3)
),
latest_survey AS (
    SELECT DISTINCT ON ("世代", BTRIM("编号"))
        "世代",
        BTRIM("编号") AS "编号",
        "调查日期",
        NULLIF(BTRIM(COALESCE("危害程度", '')), '') AS "危害程度",
        "平均虫口数"
    FROM survey."国槐尺蠖幼虫调查表"
    WHERE
        "年份" = $1
        AND BTRIM(COALESCE("编号", '')) <> ''
    ORDER BY "世代", BTRIM("编号"), "调查日期" DESC, "编号"
),
survey_stats AS (
    SELECT
        "世代",
        COUNT(*)::integer AS surveyed_points,
        COUNT(*) FILTER (
            WHERE "危害程度" IN ('轻', '中', '重')
        )::integer AS damaged_points,
        COUNT(*) FILTER (WHERE "危害程度" = '轻')::integer AS light_points,
        COUNT(*) FILTER (WHERE "危害程度" = '中')::integer AS medium_points,
        COUNT(*) FILTER (WHERE "危害程度" = '重')::integer AS severe_points,
        AVG("平均虫口数") FILTER (
            WHERE "危害程度" IN ('轻', '中', '重')
        ) AS avg_insect_count,
        MIN("调查日期") AS start_date,
        MAX("调查日期") AS end_date
    FROM latest_survey
    GROUP BY "世代"
),
ledger_stats AS (
    SELECT
        "世代",
        COUNT(*)::integer AS ledger_points,
        COUNT(*) FILTER (
            WHERE BTRIM(COALESCE("当前状态", '')) = '待防治'
        )::integer AS pending_treatment,
        COUNT(*) FILTER (
            WHERE BTRIM(COALESCE("当前状态", '')) = '待复查'
        )::integer AS pending_recheck,
        COUNT(*) FILTER (
            WHERE BTRIM(COALESCE("当前状态", '')) = '复查异常'
        )::integer AS recheck_abnormal,
        COUNT(*) FILTER (
            WHERE BTRIM(COALESCE("当前状态", '')) = '已闭环'
        )::integer AS closed_points
    FROM ledger."国槐尺蠖问题点位台账"
    WHERE "年份" = $1
    GROUP BY "世代"
)
SELECT
    g."世代",
    g.sort_order,
    $1::integer AS year,
    CURRENT_DATE AS as_of_date,
    COALESCE(s.surveyed_points, 0)::integer AS surveyed_points,
    COALESCE(s.damaged_points, 0)::integer AS damaged_points,
    COALESCE(s.light_points, 0)::integer AS light_points,
    COALESCE(s.medium_points, 0)::integer AS medium_points,
    COALESCE(s.severe_points, 0)::integer AS severe_points,
    s.avg_insect_count,
    s.start_date,
    s.end_date,
    COALESCE(l.ledger_points, 0)::integer AS ledger_points,
    COALESCE(l.pending_treatment, 0)::integer AS pending_treatment,
    COALESCE(l.pending_recheck, 0)::integer AS pending_recheck,
    COALESCE(l.recheck_abnormal, 0)::integer AS recheck_abnormal,
    COALESCE(l.closed_points, 0)::integer AS closed_points
FROM generations AS g
LEFT JOIN survey_stats AS s
  ON s."世代" = g."世代"
LEFT JOIN ledger_stats AS l
  ON l."世代" = g."世代"
ORDER BY g.sort_order
"""

SOPHORA_LOCALITY_SUMMARY_SQL = f"""
WITH latest_survey AS (
    SELECT DISTINCT ON (l."世代", BTRIM(l."编号"))
        l."世代",
        BTRIM(l."编号") AS "编号",
        l."调查日期",
        NULLIF(BTRIM(COALESCE(l."危害程度", '')), '') AS "危害程度",
        l."平均虫口数",
        BTRIM(COALESCE(s."属地", '')) AS loc_raw,
        BTRIM(COALESCE(s."村", '')) AS "村"
    FROM survey."国槐尺蠖幼虫调查表" AS l
    LEFT JOIN sites."国槐点位基础表" AS s
      ON BTRIM(s."编号") = BTRIM(l."编号")
    WHERE
        l."年份" = $1
        AND BTRIM(COALESCE(l."编号", '')) <> ''
        AND ($2::text IS NULL OR l."世代" = $2::text)
    ORDER BY l."世代", BTRIM(l."编号"), l."调查日期" DESC, l."编号"
),
classified AS (
    SELECT
        *,
        {_LOC_FROM_RAW} AS locality
    FROM latest_survey
),
site_base AS (
    SELECT
        {_LOC_FROM_SITE} AS locality,
        COUNT(*)::integer AS monitor_points
    FROM sites."国槐点位基础表"
    WHERE BTRIM(COALESCE("编号", '')) <> ''
    GROUP BY 1
),
survey_agg AS (
    SELECT
        locality,
        COUNT(*)::integer AS surveyed_points,
        COUNT(*) FILTER (
            WHERE "危害程度" IN ('轻', '中', '重')
        )::integer AS damaged_points,
        COUNT(*) FILTER (WHERE "危害程度" = '轻')::integer AS light_points,
        COUNT(*) FILTER (WHERE "危害程度" = '中')::integer AS medium_points,
        COUNT(*) FILTER (WHERE "危害程度" = '重')::integer AS severe_points,
        AVG("平均虫口数") FILTER (
            WHERE "危害程度" IN ('轻', '中', '重')
        ) AS avg_insect_count
    FROM classified
    GROUP BY locality
),
ledger_raw AS (
    SELECT
        BTRIM(COALESCE("属地", '')) AS loc_raw,
        BTRIM(COALESCE("当前状态", '')) AS status
    FROM ledger."国槐尺蠖问题点位台账"
    WHERE
        "年份" = $1
        AND ($2::text IS NULL OR "世代" = $2::text)
),
ledger_classified AS (
    SELECT
        {_LOC_FROM_RAW} AS locality,
        status
    FROM ledger_raw
),
ledger_agg AS (
    SELECT
        locality,
        COUNT(*)::integer AS ledger_points,
        COUNT(*) FILTER (WHERE status = '待防治')::integer AS pending_treatment,
        COUNT(*) FILTER (WHERE status = '待复查')::integer AS pending_recheck,
        COUNT(*) FILTER (WHERE status = '复查异常')::integer AS recheck_abnormal,
        COUNT(*) FILTER (WHERE status = '已闭环')::integer AS closed_points
    FROM ledger_classified
    GROUP BY locality
),
all_localities AS (
    SELECT locality FROM site_base
    UNION
    SELECT locality FROM survey_agg
    UNION
    SELECT locality FROM ledger_agg
)
SELECT
    a.locality,
    COALESCE(b.monitor_points, 0)::integer AS monitor_points,
    COALESCE(s.surveyed_points, 0)::integer AS surveyed_points,
    COALESCE(s.damaged_points, 0)::integer AS damaged_points,
    COALESCE(s.light_points, 0)::integer AS light_points,
    COALESCE(s.medium_points, 0)::integer AS medium_points,
    COALESCE(s.severe_points, 0)::integer AS severe_points,
    s.avg_insect_count,
    COALESCE(l.ledger_points, 0)::integer AS ledger_points,
    COALESCE(l.pending_treatment, 0)::integer AS pending_treatment,
    COALESCE(l.pending_recheck, 0)::integer AS pending_recheck,
    COALESCE(l.recheck_abnormal, 0)::integer AS recheck_abnormal,
    COALESCE(l.closed_points, 0)::integer AS closed_points
FROM all_localities AS a
LEFT JOIN site_base AS b ON b.locality = a.locality
LEFT JOIN survey_agg AS s ON s.locality = a.locality
LEFT JOIN ledger_agg AS l ON l.locality = a.locality
"""

SOPHORA_LOCALITY_SEVERE_SITES_SQL = f"""
WITH latest_survey AS (
    SELECT DISTINCT ON (l."世代", BTRIM(l."编号"))
        l."世代",
        BTRIM(l."编号") AS "编号",
        l."调查日期",
        NULLIF(BTRIM(COALESCE(l."危害程度", '')), '') AS "危害程度",
        l."平均虫口数",
        BTRIM(COALESCE(s."属地", '')) AS loc_raw,
        BTRIM(COALESCE(s."村", '')) AS "村"
    FROM survey."国槐尺蠖幼虫调查表" AS l
    LEFT JOIN sites."国槐点位基础表" AS s
      ON BTRIM(s."编号") = BTRIM(l."编号")
    WHERE
        l."年份" = $1
        AND BTRIM(COALESCE(l."编号", '')) <> ''
        AND ($2::text IS NULL OR l."世代" = $2::text)
    ORDER BY l."世代", BTRIM(l."编号"), l."调查日期" DESC, l."编号"
),
classified AS (
    SELECT
        *,
        {_LOC_FROM_RAW} AS locality
    FROM latest_survey
    WHERE "危害程度" = '重'
),
ledger_status AS (
    SELECT DISTINCT ON ("世代", BTRIM("编号"))
        "世代",
        BTRIM("编号") AS "编号",
        NULLIF(BTRIM(COALESCE("当前状态", '')), '') AS status
    FROM ledger."国槐尺蠖问题点位台账"
    WHERE
        "年份" = $1
        AND ($2::text IS NULL OR "世代" = $2::text)
        AND BTRIM(COALESCE("编号", '')) <> ''
    ORDER BY "世代", BTRIM("编号")
)
SELECT
    c.locality,
    c."编号" AS code,
    COALESCE(NULLIF(c."村", ''), '--') AS name,
    COALESCE(c."平均虫口数", 0)::integer AS avg_insect_count,
    c."调查日期" AS survey_date,
    ls.status AS ledger_status
FROM classified AS c
LEFT JOIN ledger_status AS ls
  ON ls."编号" = c."编号"
 AND ls."世代" = c."世代"
ORDER BY c.locality, c."平均虫口数" DESC NULLS LAST, c."编号"
"""
