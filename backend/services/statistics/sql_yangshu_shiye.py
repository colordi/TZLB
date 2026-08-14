from __future__ import annotations

# 杨树食叶害虫调查整体汇总：调查结论只有「发现问题 / 未发现问题」两类，
# 未发现问题数在服务层用 总记录数 - 发现问题记录数 得出。
YANGSHU_SHIYE_TOTALS_SQL = """
SELECT
    COUNT(*)::integer AS survey_records,
    COUNT(DISTINCT BTRIM("编号"))::integer AS surveyed_points,
    COUNT(*) FILTER (WHERE BTRIM("调查结论") = '发现问题')::integer AS problem_records,
    COUNT(DISTINCT BTRIM("编号")) FILTER (WHERE BTRIM("调查结论") = '发现问题')::integer AS problem_points,
    MAX("调查日期") AS last_survey_date
FROM
    survey."杨树食叶害虫调查表"
WHERE
    ($1::integer IS NULL OR "年份" = $1::integer)
"""

# 台账问题点位按当前状态计数；状态枚举不写死，新状态自动出现
YANGSHU_SHIYE_STATUS_SQL = """
SELECT
    NULLIF(BTRIM("当前状态"), '') AS status,
    COUNT(*)::integer AS count
FROM
    ledger."杨树食叶害虫问题点位台账"
WHERE
    ($1::integer IS NULL OR "年份" = $1::integer)
GROUP BY
    1
ORDER BY
    count DESC,
    status
"""

# 虫害类型没有固定枚举，按调查表实际出现的类型分组
YANGSHU_SHIYE_PEST_TYPE_SQL = """
SELECT
    BTRIM("虫害类型") AS pest_type,
    COUNT(*)::integer AS survey_records,
    COUNT(*) FILTER (WHERE BTRIM("调查结论") = '发现问题')::integer AS problem_records,
    COUNT(DISTINCT BTRIM("编号")) FILTER (WHERE BTRIM("调查结论") = '发现问题')::integer AS problem_points,
    MAX("调查日期") AS last_survey_date
FROM
    survey."杨树食叶害虫调查表"
WHERE
    ($1::integer IS NULL OR "年份" = $1::integer)
GROUP BY
    1
ORDER BY
    survey_records DESC,
    pest_type
"""
