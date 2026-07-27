-- 其他害虫调查表增加「点位名称」，与美国白蛾调查表一致：
-- 工单候选/日期现场照片从调查记录读取名称，不再只依赖 sites 基础表。

BEGIN;

ALTER TABLE survey."其他害虫调查表"
  ADD COLUMN IF NOT EXISTS "点位名称" character varying;

-- 优先用基础点位表名称回填
UPDATE survey."其他害虫调查表" AS i
SET "点位名称" = NULLIF(BTRIM(s."点位名称"), '')
FROM sites."其他害虫点位基础表" AS s
WHERE i."编号" = s."编号"
  AND (i."点位名称" IS NULL OR BTRIM(i."点位名称") = '')
  AND NULLIF(BTRIM(s."点位名称"), '') IS NOT NULL;

-- 基础表仍空时，用事件流水最近一条非空名称回填
UPDATE survey."其他害虫调查表" AS i
SET "点位名称" = src."点位名称"
FROM (
  SELECT DISTINCT ON (e."编号")
    e."编号",
    NULLIF(BTRIM(e."点位名称"), '') AS "点位名称"
  FROM ledger."其他害虫问题点位事件流水表" AS e
  WHERE NULLIF(BTRIM(e."点位名称"), '') IS NOT NULL
  ORDER BY e."编号", e."事件时间" DESC, e.id DESC
) AS src
WHERE i."编号" = src."编号"
  AND (i."点位名称" IS NULL OR BTRIM(i."点位名称") = '');

-- 仍无名称时，用编号兜底（路名类「未发现问题」记录常用路名作编号）
UPDATE survey."其他害虫调查表"
SET "点位名称" = "编号"
WHERE ("点位名称" IS NULL OR BTRIM("点位名称") = '')
  AND NULLIF(BTRIM("编号"), '') IS NOT NULL;

UPDATE survey."其他害虫调查表"
SET "点位名称" = ''
WHERE "点位名称" IS NULL;

ALTER TABLE survey."其他害虫调查表"
  ALTER COLUMN "点位名称" SET DEFAULT '';

ALTER TABLE survey."其他害虫调查表"
  ALTER COLUMN "点位名称" SET NOT NULL;

COMMENT ON COLUMN survey."其他害虫调查表"."点位名称" IS
  '调查记录上的点位名称；工单素材/调查导入优先使用本字段';

COMMIT;
