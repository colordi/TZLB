-- 其他害虫点位地图视图：完全参照 views."美国白蛾点位" 的结构，
-- 仅保留核心点位字段（geom、编号、属地、点位名称），
-- 替代 views."其他害虫调查"（原视图含害虫类型、调查日期、年份等调查字段）。
DROP VIEW IF EXISTS views."其他害虫调查";

CREATE VIEW views."其他害虫点位" AS
SELECT
    s.geom,
    BTRIM(s."编号") AS "编号",
    NULLIF(BTRIM(s."属地"), '') AS "属地",
    NULLIF(BTRIM(COALESCE(s."点位名称", '')), '') AS "点位名称"
FROM sites."其他害虫点位基础表" AS s
WHERE s.geom IS NOT NULL;

COMMENT ON VIEW views."其他害虫点位"
    IS '其他害虫基础点位地图视图，供调查员在地图端新增和查看点位';
