-- 阶段2迁移：重建 views 视图
-- 视图去年度前缀，按 年份/世代 列筛选
-- 前置条件：20260705_01_schema_migration.sql 已执行

BEGIN;

-- 旧视图已在 20260705_01_schema_migration.sql 中 DROP

-- ============================================================
-- 1. 美国白蛾调查（替代 2026_美国白蛾第 1 代调查）
-- ============================================================
CREATE OR REPLACE VIEW views."美国白蛾调查" AS
WITH
generations ("世代") AS (
    VALUES ('第一代'), ('第二代'), ('第三代')
),
latest_per_gen AS (
    SELECT DISTINCT ON (i."编号", i."年份", i."世代")
        BTRIM(i."编号") AS "编号",
        i."调查日期",
        i."年份",
        i."世代"
    FROM survey."美国白蛾调查表" AS i
    WHERE BTRIM(COALESCE(i."编号", '')) <> ''
    ORDER BY i."编号", i."年份", i."世代", i."调查日期" DESC
)
SELECT
    c.geom,
    BTRIM(c."点位编号") AS "编号",
    COALESCE(NULLIF(BTRIM(c."属地"), ''), '') AS "属地",
    COALESCE(NULLIF(BTRIM(c."点位名称"), ''), '') AS "点位名称",
    l."调查日期",
    EXTRACT(YEAR FROM CURRENT_DATE)::integer AS "年份",
    g."世代"
FROM reference."通州区小区边界" AS c
CROSS JOIN generations AS g
LEFT JOIN latest_per_gen AS l
    ON l."编号" = BTRIM(c."点位编号")
    AND l."世代" = g."世代"
    AND l."年份" = EXTRACT(YEAR FROM CURRENT_DATE)::integer;

-- ============================================================
-- 2. 国槐尺蠖幼虫调查（替代 2026_国槐尺蠖幼虫调查）
-- ============================================================
CREATE OR REPLACE VIEW views."国槐尺蠖幼虫调查" AS
SELECT
    s.geom,
    s."编号",
    s."属地",
    NULLIF(BTRIM(s."村"), '') AS "点位名称",
    l."调查日期",
    l."危害程度",
    l."年份",
    l."世代"
FROM sites."国槐点位基础表" AS s
LEFT JOIN (
    SELECT
        c."编号",
        max(c."调查日期") AS "调查日期",
        CASE max(
            CASE BTRIM(COALESCE(c."危害程度", ''))
                WHEN '白' THEN 1 WHEN '无需防治' THEN 1 WHEN '轻' THEN 2
                WHEN '中' THEN 3 WHEN '重' THEN 4 ELSE 0
            END)
            WHEN 1 THEN '白' WHEN 2 THEN '轻' WHEN 3 THEN '中' WHEN 4 THEN '重'
            ELSE NULL
        END::character varying AS "危害程度",
        max(c."年份") AS "年份",
        max(c."世代") AS "世代"
    FROM survey."国槐尺蠖幼虫调查表" AS c
    GROUP BY c."编号"
) AS l ON s."编号" = l."编号";

-- ============================================================
-- 3. 春尺蠖幼虫调查（替代 2026_春尺蠖幼虫调查）
-- WHERE 从 春尺蠖_2026年成虫发生情况 <> '伐' 改为 当前点位状态 <> '伐除'
-- ============================================================
CREATE OR REPLACE VIEW views."春尺蠖幼虫调查" AS
SELECT
    s.geom,
    s."编号",
    s."属地",
    NULLIF(BTRIM(s."村"), '') AS "点位名称",
    l."调查日期",
    l."危害程度",
    l."年份"
FROM sites."杨树点位基础表" AS s
LEFT JOIN (
    SELECT
        c."编号",
        max(c."调查日期") AS "调查日期",
        CASE max(
            CASE BTRIM(COALESCE(c."危害程度", ''))
                WHEN '白' THEN 1 WHEN '无需防治' THEN 1 WHEN '轻' THEN 2
                WHEN '中' THEN 3 WHEN '重' THEN 4 ELSE 0
            END)
            WHEN 1 THEN '白' WHEN 2 THEN '轻' WHEN 3 THEN '中' WHEN 4 THEN '重'
            ELSE NULL
        END::character varying AS "危害程度",
        max(c."年份") AS "年份"
    FROM survey."春尺蠖幼虫调查表" AS c
    GROUP BY c."编号"
) AS l ON s."编号" = l."编号"
WHERE s."当前点位状态" <> '伐除';

-- ============================================================
-- 4. 春尺蠖成虫调查（替代 2026_春尺蠖成虫调查）
-- WHERE 从 春尺蠖_2026年_围环发生情况 = '可调查' 改为 当前点位状态 = '可调查'
-- ============================================================
CREATE OR REPLACE VIEW views."春尺蠖成虫调查" AS
SELECT
    s.geom,
    s."编号",
    s."属地",
    NULLIF(BTRIM(s."村"), '') AS "点位名称",
    a."调查日期",
    a."危害程度",
    a."年份"
FROM sites."杨树点位基础表" AS s
LEFT JOIN (
    SELECT
        c."编号",
        max(c."调查日期") AS "调查日期",
        CASE max(
            CASE BTRIM(COALESCE(c."受害程度", ''))
                WHEN '白' THEN 1 WHEN '无需防治' THEN 1 WHEN '轻' THEN 2
                WHEN '中' THEN 3 WHEN '重' THEN 4 ELSE 0
            END)
            WHEN 1 THEN '白' WHEN 2 THEN '轻' WHEN 3 THEN '中' WHEN 4 THEN '重'
            ELSE NULL
        END::character varying AS "危害程度",
        max(c."年份") AS "年份"
    FROM survey."春尺蠖成虫调查表" AS c
    GROUP BY c."编号"
) AS a ON s."编号" = a."编号"
WHERE s."当前点位状态" = '可调查';

-- ============================================================
-- 5. 其他害虫调查（替代 2026_其他害虫调查）
-- ============================================================
CREATE OR REPLACE VIEW views."其他害虫调查" AS
WITH latest_inspection AS (
    SELECT DISTINCT ON (i."编号", i."虫害类型")
        i."编号",
        i."虫害类型",
        i."调查日期",
        i."年份"
    FROM survey."其他害虫调查表" AS i
    ORDER BY i."编号", i."虫害类型", i."调查日期" DESC
)
SELECT
    s.geom,
    s."编号",
    s."属地",
    s."点位名称",
    NULLIF(BTRIM(l."虫害类型"), '') AS "害虫类型",
    l."调查日期",
    l."年份"
FROM sites."其他害虫点位基础表" AS s
LEFT JOIN latest_inspection AS l
    ON l."编号" = s."编号";

-- ============================================================
-- 6. 国槐尺蠖幼虫历年发生情况（重建：改为 JOIN survey 按年份聚合）
-- 原 CROSS JOIN LATERAL VALUES 展开 sites 宽字段，现直接查 survey 表
-- ============================================================
CREATE OR REPLACE VIEW views."国槐尺蠖幼虫历年发生情况" AS
SELECT
    s.geom,
    s."编号",
    s."属地",
    NULLIF(BTRIM(s."村"), '') AS "点位名称",
    c."年份",
    NULLIF(BTRIM(c."危害程度"), '')::character varying AS "危害程度"
FROM sites."国槐点位基础表" AS s
JOIN (
    SELECT
        i."编号",
        i."年份",
        CASE max(
            CASE BTRIM(COALESCE(i."危害程度", ''))
                WHEN '白' THEN 1 WHEN '无需防治' THEN 1 WHEN '轻' THEN 2
                WHEN '中' THEN 3 WHEN '重' THEN 4 ELSE 0
            END)
            WHEN 1 THEN '白' WHEN 2 THEN '轻' WHEN 3 THEN '中' WHEN 4 THEN '重'
            ELSE NULL
        END::text AS "危害程度"
    FROM survey."国槐尺蠖幼虫调查表" AS i
    GROUP BY i."编号", i."年份"
) AS c ON s."编号" = c."编号"
WHERE s.geom IS NOT NULL
  AND NULLIF(BTRIM(COALESCE(c."危害程度", '')), '') IS NOT NULL;

COMMIT;
