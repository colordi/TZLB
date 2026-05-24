CREATE SCHEMA IF NOT EXISTS views;

CREATE OR REPLACE VIEW views."2026_美国白蛾第 1 代调查" AS
WITH normalized_inspection AS (
    SELECT
        BTRIM(i."编号") AS "编号",
        i."调查日期",
        NULLIF(BTRIM(i."区域"), '') AS "区域",
        NULLIF(BTRIM(i."发生位置"), '') AS "发生位置",
        NULLIF(BTRIM(i."绿地性质"), '') AS "绿地性质",
        NULLIF(BTRIM(i."危害寄主"), '') AS "危害寄主",
        COALESCE(i."受害株数", 0) AS "受害株数",
        COALESCE(i."网幕数量", 0) AS "网幕数量",
        NULLIF(BTRIM(i."是否剪网"), '') AS "是否剪网",
        NULLIF(BTRIM(i."剪网彻底"), '') AS "剪网彻底",
        NULLIF(BTRIM(i."详细描述"), '') AS "详细描述",
        NULLIF(BTRIM(i."备注"), '') AS "备注"
    FROM survey.mei_guo_bai_e_first_generation_inspection AS i
    WHERE BTRIM(COALESCE(i."编号", '')) <> ''
),
latest_inspection AS (
    SELECT DISTINCT ON (i."编号")
        i."编号",
        i."调查日期",
        i."区域",
        i."发生位置",
        i."绿地性质",
        i."危害寄主",
        i."受害株数",
        i."网幕数量",
        i."是否剪网",
        i."剪网彻底",
        i."详细描述",
        i."备注"
    FROM normalized_inspection AS i
    ORDER BY i."编号", i."调查日期" DESC
),
inspection_summary AS (
    SELECT
        i."编号",
        count(*)::integer AS "调查次数",
        sum(i."受害株数")::integer AS "累计受害株数",
        sum(i."网幕数量")::integer AS "累计网幕数量"
    FROM normalized_inspection AS i
    GROUP BY i."编号"
)
SELECT
    c.id,
    c.geom,
    BTRIM(c."点位编号") AS "编号",
    NULLIF(BTRIM(c."乡镇"), '') AS "乡镇",
    NULLIF(BTRIM(c."点位名称"), '') AS "点位名称",
    c."面积",
    c."25年1代受害株" AS "2025年1代受害株",
    c."25年2代受害株" AS "2025年2代受害株",
    c."25年3代受害株" AS "2025年3代受害株",
    c."25年景观害虫发生" AS "2025年景观害虫发生",
    l."调查日期",
    CASE
        WHEN l."调查日期" IS NULL THEN '未调查'
        ELSE '调查'
    END::character varying AS "调查状态",
    COALESCE(s."调查次数", 0) AS "调查次数",
    COALESCE(s."累计受害株数", 0) AS "累计受害株数",
    COALESCE(s."累计网幕数量", 0) AS "累计网幕数量",
    l."区域",
    l."发生位置",
    l."绿地性质",
    l."危害寄主",
    l."受害株数",
    l."网幕数量",
    l."是否剪网",
    l."剪网彻底",
    l."详细描述",
    l."备注"
FROM reference.tongzhou_communities AS c
LEFT JOIN latest_inspection AS l
  ON l."编号" = BTRIM(c."点位编号")
LEFT JOIN inspection_summary AS s
  ON s."编号" = BTRIM(c."点位编号");

COMMENT ON VIEW views."2026_美国白蛾第 1 代调查"
    IS '2026年美国白蛾第1代调查地图视图，由通州社区点位关联最新巡查记录生成';
