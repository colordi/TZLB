from __future__ import annotations

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
