from __future__ import annotations

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
