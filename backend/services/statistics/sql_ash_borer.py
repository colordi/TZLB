from __future__ import annotations

# 每个调查点位固定调查 30 株。死亡率 / 有虫株率的分母均为「有效点位数 × 30」。
ASH_BORER_TREES_PER_POINT = 30
# 危害程度按点位有虫株率：0 为无；≤10%（1–3 株）为轻；≤20%（4–6 株）为中；>20%（≥7 株）为重。
ASH_BORER_LIGHT_MAX_PLANTS = 3
ASH_BORER_MEDIUM_MAX_PLANTS = 6

# 白蜡蛀干害虫调查整体汇总：只有调查表（无台账）。
# 存在换植（换植（株）> 0）的点位整点排除，不参与株数合计与率值计算。
ASH_BORER_TOTALS_SQL = """
WITH year_rows AS (
    SELECT *
    FROM survey."白蜡蛀干害虫调查表"
    WHERE
        ($1::integer IS NULL OR "年份" = $1::integer)
),
eligible AS (
    SELECT *
    FROM year_rows
    WHERE COALESCE("换植（株）", 0) = 0
)
SELECT
    COUNT(*)::integer AS survey_records,
    COUNT(DISTINCT BTRIM("编号"))::integer AS surveyed_points,
    (
        SELECT COUNT(*)::integer
        FROM year_rows
        WHERE COALESCE("换植（株）", 0) > 0
    ) AS excluded_points,
    MAX("调查日期") AS last_survey_date,
    COALESCE(SUM("窄吉丁危害（株）"), 0)::integer AS agrilus_damaged_plants,
    COALESCE(SUM("窄吉丁孔数（个）"), 0)::integer AS agrilus_holes,
    COALESCE(SUM("木蠹蛾危害（株）"), 0)::integer AS cossus_damaged_plants,
    COALESCE(SUM("目测死亡（株）"), 0)::integer AS dead_plants,
    COALESCE(SUM("伐除（株）"), 0)::integer AS felled_plants,
    COUNT(*) FILTER (WHERE COALESCE("窄吉丁危害（株）", 0) = 0)::integer AS agrilus_none,
    COUNT(*) FILTER (
        WHERE COALESCE("窄吉丁危害（株）", 0) BETWEEN 1 AND 3
    )::integer AS agrilus_light,
    COUNT(*) FILTER (
        WHERE COALESCE("窄吉丁危害（株）", 0) BETWEEN 4 AND 6
    )::integer AS agrilus_medium,
    COUNT(*) FILTER (
        WHERE COALESCE("窄吉丁危害（株）", 0) >= 7
    )::integer AS agrilus_high,
    COUNT(*) FILTER (WHERE COALESCE("木蠹蛾危害（株）", 0) = 0)::integer AS cossus_none,
    COUNT(*) FILTER (
        WHERE COALESCE("木蠹蛾危害（株）", 0) BETWEEN 1 AND 3
    )::integer AS cossus_light,
    COUNT(*) FILTER (
        WHERE COALESCE("木蠹蛾危害（株）", 0) BETWEEN 4 AND 6
    )::integer AS cossus_medium,
    COUNT(*) FILTER (
        WHERE COALESCE("木蠹蛾危害（株）", 0) >= 7
    )::integer AS cossus_high
FROM
    eligible
"""

# 属地没有固定枚举，按调查表实际出现的属地分组；同样先排除换植点位。
ASH_BORER_LOCALITY_SQL = """
WITH year_rows AS (
    SELECT *
    FROM survey."白蜡蛀干害虫调查表"
    WHERE
        ($1::integer IS NULL OR "年份" = $1::integer)
)
SELECT
    NULLIF(BTRIM("属地"), '') AS locality,
    COUNT(*) FILTER (WHERE COALESCE("换植（株）", 0) = 0)::integer AS survey_records,
    COUNT(DISTINCT BTRIM("编号")) FILTER (
        WHERE COALESCE("换植（株）", 0) = 0
    )::integer AS surveyed_points,
    COUNT(*) FILTER (WHERE COALESCE("换植（株）", 0) > 0)::integer AS excluded_points,
    COALESCE(
        SUM("窄吉丁危害（株）") FILTER (WHERE COALESCE("换植（株）", 0) = 0),
        0
    )::integer AS agrilus_damaged_plants,
    COALESCE(
        SUM("木蠹蛾危害（株）") FILTER (WHERE COALESCE("换植（株）", 0) = 0),
        0
    )::integer AS cossus_damaged_plants,
    COALESCE(
        SUM("目测死亡（株）") FILTER (WHERE COALESCE("换植（株）", 0) = 0),
        0
    )::integer AS dead_plants,
    COALESCE(
        SUM("伐除（株）") FILTER (WHERE COALESCE("换植（株）", 0) = 0),
        0
    )::integer AS felled_plants,
    COUNT(*) FILTER (
        WHERE COALESCE("换植（株）", 0) = 0 AND COALESCE("窄吉丁危害（株）", 0) = 0
    )::integer AS agrilus_none,
    COUNT(*) FILTER (
        WHERE COALESCE("换植（株）", 0) = 0
          AND COALESCE("窄吉丁危害（株）", 0) BETWEEN 1 AND 3
    )::integer AS agrilus_light,
    COUNT(*) FILTER (
        WHERE COALESCE("换植（株）", 0) = 0
          AND COALESCE("窄吉丁危害（株）", 0) BETWEEN 4 AND 6
    )::integer AS agrilus_medium,
    COUNT(*) FILTER (
        WHERE COALESCE("换植（株）", 0) = 0 AND COALESCE("窄吉丁危害（株）", 0) >= 7
    )::integer AS agrilus_high,
    COUNT(*) FILTER (
        WHERE COALESCE("换植（株）", 0) = 0 AND COALESCE("木蠹蛾危害（株）", 0) = 0
    )::integer AS cossus_none,
    COUNT(*) FILTER (
        WHERE COALESCE("换植（株）", 0) = 0
          AND COALESCE("木蠹蛾危害（株）", 0) BETWEEN 1 AND 3
    )::integer AS cossus_light,
    COUNT(*) FILTER (
        WHERE COALESCE("换植（株）", 0) = 0
          AND COALESCE("木蠹蛾危害（株）", 0) BETWEEN 4 AND 6
    )::integer AS cossus_medium,
    COUNT(*) FILTER (
        WHERE COALESCE("换植（株）", 0) = 0 AND COALESCE("木蠹蛾危害（株）", 0) >= 7
    )::integer AS cossus_high,
    MAX("调查日期") FILTER (WHERE COALESCE("换植（株）", 0) = 0) AS last_survey_date
FROM
    year_rows
GROUP BY
    1
HAVING
    COUNT(*) FILTER (WHERE COALESCE("换植（株）", 0) = 0) > 0
ORDER BY
    surveyed_points DESC,
    locality
"""
