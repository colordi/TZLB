-- 美国白蛾小区点位基础表：从 reference.通州区小区边界 提取面内点，独立于道路点位基础表
-- 同时重建 views.美国白蛾调查，图层由面改为点

BEGIN;

-- ============================================================
-- 1. sites.美国白蛾小区点位基础表（独立物理表，一次性回填）
-- ============================================================
CREATE TABLE IF NOT EXISTS sites."美国白蛾小区点位基础表" (
    id BIGSERIAL PRIMARY KEY,
    "编号" character varying NOT NULL,
    "属地" character varying,
    "点位名称" character varying,
    "面积" double precision,
    geom geometry(Point, 4326)
);

-- 幂等回填：仅当目标表为空时执行；ST_PointOnSurface 保证点落在面内
INSERT INTO sites."美国白蛾小区点位基础表" ("编号", "属地", "点位名称", "面积", geom)
SELECT
    BTRIM(c."点位编号") AS "编号",
    NULLIF(BTRIM(c."属地"), '') AS "属地",
    NULLIF(BTRIM(c."点位名称"), '') AS "点位名称",
    c."面积",
    ST_Transform(ST_PointOnSurface(c.geom), 4326) AS geom
FROM reference."通州区小区边界" AS c
WHERE c.geom IS NOT NULL
  AND BTRIM(COALESCE(c."点位编号", '')) <> ''
  AND NOT EXISTS (SELECT 1 FROM sites."美国白蛾小区点位基础表");

CREATE UNIQUE INDEX IF NOT EXISTS idx_white_moth_parcel_sites_code
    ON sites."美国白蛾小区点位基础表" ("编号");

COMMENT ON TABLE sites."美国白蛾小区点位基础表"
    IS '美国白蛾小区点位基础表（自 reference.通州区小区边界 提取面内点）';

-- ============================================================
-- 2. 重建 views.美国白蛾调查：小区面 -> 小区点位
-- 输出列保持不变，仅数据来源换成新基础表
-- geom 类型变化（MultiPolygon/3857 -> Point/4326）不能直接 REPLACE，先 DROP
-- ============================================================
DROP VIEW IF EXISTS views."美国白蛾调查";

CREATE VIEW views."美国白蛾调查" AS
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
    s.geom,
    s."编号",
    COALESCE(NULLIF(BTRIM(s."属地"), ''), '') AS "属地",
    COALESCE(NULLIF(BTRIM(s."点位名称"), ''), '') AS "点位名称",
    l."调查日期",
    EXTRACT(YEAR FROM CURRENT_DATE)::integer AS "年份",
    g."世代"
FROM sites."美国白蛾小区点位基础表" AS s
CROSS JOIN generations AS g
LEFT JOIN latest_per_gen AS l
    ON l."编号" = s."编号"
    AND l."世代" = g."世代"
    AND l."年份" = EXTRACT(YEAR FROM CURRENT_DATE)::integer;

COMMIT;
