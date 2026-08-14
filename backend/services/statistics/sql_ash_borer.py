from __future__ import annotations

# 白蜡蛀干害虫调查整体汇总：只有调查表（无台账），按株数指标合计。
ASH_BORER_TOTALS_SQL = """
SELECT
    COUNT(*)::integer AS survey_records,
    COUNT(DISTINCT BTRIM("编号"))::integer AS surveyed_points,
    MAX("调查日期") AS last_survey_date,
    COALESCE(SUM("窄吉丁危害（株）"), 0)::integer AS agrilus_damaged_plants,
    COALESCE(SUM("窄吉丁孔数（个）"), 0)::integer AS agrilus_holes,
    COALESCE(SUM("木蠹蛾危害（株）"), 0)::integer AS cossus_damaged_plants,
    COALESCE(SUM("目测死亡（株）"), 0)::integer AS dead_plants,
    COALESCE(SUM("伐除（株）"), 0)::integer AS felled_plants,
    COALESCE(SUM("换植（株）"), 0)::integer AS replanted_plants
FROM
    survey."白蜡蛀干害虫调查表"
WHERE
    ($1::integer IS NULL OR "年份" = $1::integer)
"""

# 属地没有固定枚举，按调查表实际出现的属地分组
ASH_BORER_LOCALITY_SQL = """
SELECT
    NULLIF(BTRIM("属地"), '') AS locality,
    COUNT(*)::integer AS survey_records,
    COUNT(DISTINCT BTRIM("编号"))::integer AS surveyed_points,
    COALESCE(SUM("窄吉丁危害（株）"), 0)::integer AS agrilus_damaged_plants,
    COALESCE(SUM("木蠹蛾危害（株）"), 0)::integer AS cossus_damaged_plants,
    COALESCE(SUM("目测死亡（株）"), 0)::integer AS dead_plants,
    COALESCE(SUM("伐除（株）"), 0)::integer AS felled_plants,
    COALESCE(SUM("换植（株）"), 0)::integer AS replanted_plants,
    MAX("调查日期") AS last_survey_date
FROM
    survey."白蜡蛀干害虫调查表"
WHERE
    ($1::integer IS NULL OR "年份" = $1::integer)
GROUP BY
    1
ORDER BY
    survey_records DESC,
    locality
"""
