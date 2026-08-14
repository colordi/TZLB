from __future__ import annotations

# 春尺蠖成虫/幼虫调查汇总：虫口规模取 平均虫口数 的均值与 总虫口数 的合计。
SPRING_INCHWORM_ADULT_TOTALS_SQL = """
SELECT
    COUNT(*)::integer AS survey_records,
    COUNT(DISTINCT BTRIM("编号"))::integer AS surveyed_points,
    ROUND(AVG("平均虫口数")::numeric, 1) AS avg_insect_count,
    COALESCE(SUM("总虫口数"), 0)::integer AS total_insect_count,
    MAX("调查日期") AS last_survey_date
FROM
    survey."春尺蠖成虫调查表"
WHERE
    ($1::integer IS NULL OR "年份" = $1::integer)
"""

SPRING_INCHWORM_LARVA_TOTALS_SQL = """
SELECT
    COUNT(*)::integer AS survey_records,
    COUNT(DISTINCT BTRIM("编号"))::integer AS surveyed_points,
    ROUND(AVG("平均虫口数")::numeric, 1) AS avg_insect_count,
    COALESCE(SUM("总虫口数"), 0)::integer AS total_insect_count,
    MAX("调查日期") AS last_survey_date
FROM
    survey."春尺蠖幼虫调查表"
WHERE
    ($1::integer IS NULL OR "年份" = $1::integer)
"""

# 受害程度（成虫）/危害程度（幼虫）枚举不写死，按实际取值分组
SPRING_INCHWORM_ADULT_DAMAGE_LEVEL_SQL = """
SELECT
    NULLIF(BTRIM("受害程度"), '') AS damage_level,
    COUNT(*)::integer AS count
FROM
    survey."春尺蠖成虫调查表"
WHERE
    ($1::integer IS NULL OR "年份" = $1::integer)
GROUP BY
    1
ORDER BY
    count DESC,
    damage_level
"""

SPRING_INCHWORM_LARVA_DAMAGE_LEVEL_SQL = """
SELECT
    NULLIF(BTRIM("危害程度"), '') AS damage_level,
    COUNT(*)::integer AS count
FROM
    survey."春尺蠖幼虫调查表"
WHERE
    ($1::integer IS NULL OR "年份" = $1::integer)
GROUP BY
    1
ORDER BY
    count DESC,
    damage_level
"""

# 围环调查汇总：围环日期即调查日期
SPRING_INCHWORM_RING_TOTALS_SQL = """
SELECT
    COUNT(*)::integer AS survey_records,
    COUNT(DISTINCT BTRIM("编号"))::integer AS surveyed_points,
    COALESCE(SUM("补环数量"), 0)::integer AS repair_count,
    COALESCE(SUM("成虫数量"), 0)::integer AS adult_count,
    MAX("围环日期") AS last_survey_date
FROM
    survey."春尺蠖围环调查表"
WHERE
    ($1::integer IS NULL OR "年份" = $1::integer)
"""

# 台账问题点位按当前状态计数；状态枚举不写死，新状态自动出现
SPRING_INCHWORM_STATUS_SQL = """
SELECT
    NULLIF(BTRIM("当前状态"), '') AS status,
    COUNT(*)::integer AS count
FROM
    ledger."春尺蠖问题点位台账"
WHERE
    ($1::integer IS NULL OR "年份" = $1::integer)
GROUP BY
    1
ORDER BY
    count DESC,
    status
"""
