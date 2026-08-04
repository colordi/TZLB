from __future__ import annotations

from backend.services.statistics.sql_locality import WHITE_MOTH_CANONICAL_LOCALITIES

# 与 sql_locality 保持一致的属地归一化：清单外属地归入「其他单位」
_LOCALITY_CASE_SQL = "\n        ".join(
    f"WHEN BTRIM(COALESCE(\"属地\", '')) = '{locality}' THEN '{locality}'"
    for locality in WHITE_MOTH_CANONICAL_LOCALITIES
)

# $1 年份, $2 世代
# 「危害寄主」格式：树种/株数，多寄主以「、」分隔（如 杨/1、桑/1），实测无脏数据；
# 仍做空片段/非数字株数兜底。聚合与树种名归一化在 host_summary.py（纯 Python）完成。
WHITE_MOTH_HOST_RAW_SQL = f"""
SELECT
    BTRIM(COALESCE(l."编号", '')) AS code,
    BTRIM(split_part(host_part.part, '/', 1)) AS host_raw,
    CASE
        WHEN BTRIM(split_part(host_part.part, '/', 2)) ~ '^\\d+$'
            THEN BTRIM(split_part(host_part.part, '/', 2))::integer
        ELSE 0
    END AS plants,
    CASE
        {_LOCALITY_CASE_SQL}
        ELSE '其他单位'
    END AS locality
FROM
    ledger."美国白蛾问题点位台账" l,
    regexp_split_to_table(COALESCE(l."危害寄主", ''), '、') AS host_part(part)
WHERE
    l."年份" = $1
    AND ($2::text IS NULL OR l."世代" = $2::text)
    AND BTRIM(host_part.part) <> '';
"""
