from __future__ import annotations

# 各统计模块实际数据年份：按来源表取「年份」列去重，聚合在 service 层完成
STATISTICS_YEARS_SQL = """
SELECT module, year
FROM (
    SELECT 'white-moth' AS module, "年份" AS year FROM survey."美国白蛾调查表"
    UNION ALL
    SELECT 'white-moth' AS module, "年份" AS year FROM ledger."美国白蛾问题点位台账"
    UNION ALL
    SELECT 'poplar-inchworm' AS module, "年份" AS year FROM survey."春尺蠖成虫调查表"
    UNION ALL
    SELECT 'sophora-inchworm' AS module, "年份" AS year FROM survey."国槐尺蠖幼虫调查表"
    UNION ALL
    SELECT 'sophora-inchworm' AS module, "年份" AS year FROM ledger."国槐尺蠖问题点位台账"
    UNION ALL
    SELECT 'other-pests' AS module, "年份" AS year FROM survey."其他害虫调查表"
    UNION ALL
    SELECT 'yangshu-shiye' AS module, "年份" AS year FROM survey."杨树食叶害虫调查表"
    UNION ALL
    SELECT 'ash-borer' AS module, "年份" AS year FROM survey."白蜡蛀干害虫调查表"
) AS years_by_module
WHERE year IS NOT NULL
GROUP BY module, year
ORDER BY module, year
"""

# 前端统计模块键全集：即使某模块暂无数据也返回空列表
STATISTICS_MODULE_KEYS: tuple[str, ...] = (
    "white-moth",
    "poplar-inchworm",
    "sophora-inchworm",
    "other-pests",
    "yangshu-shiye",
    "ash-borer",
)
