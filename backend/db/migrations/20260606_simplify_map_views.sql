BEGIN;

DROP VIEW IF EXISTS views."2026_其他害虫调查";
CREATE VIEW views."2026_其他害虫调查" AS
WITH latest_inspection AS (
    SELECT DISTINCT ON (i."编号", i."虫害类型")
        i."编号",
        i."虫害类型",
        i."调查日期"
    FROM survey."其他害虫调查表" AS i
    ORDER BY i."编号", i."虫害类型", i."调查日期" DESC
)
SELECT
    s.geom,
    s."编号",
    s."属地",
    s."点位名称",
    NULLIF(BTRIM(l."虫害类型"), '') AS "害虫类型",
    l."调查日期"
FROM sites."其他害虫点位基础表" AS s
LEFT JOIN latest_inspection AS l
  ON l."编号" = s."编号";

COMMENT ON VIEW views."2026_其他害虫调查"
    IS '其他害虫调查地图视图，仅保留核心点位与调查字段';

DROP VIEW IF EXISTS views."2026_国槐尺蠖幼虫调查";
CREATE VIEW views."2026_国槐尺蠖幼虫调查" AS
SELECT
    s.geom,
    s."编号",
    s."属地",
    NULLIF(BTRIM(s."村"), '') AS "点位名称",
    l."调查日期",
    l."危害程度"
FROM sites."国槐点位基础表" AS s
LEFT JOIN (
    SELECT
        c."编号",
        max(c."调查日期") AS "调查日期",
        CASE max(
            CASE BTRIM(COALESCE(c."危害程度", ''))
                WHEN '白' THEN 1
                WHEN '无需防治' THEN 1
                WHEN '轻' THEN 2
                WHEN '中' THEN 3
                WHEN '重' THEN 4
                ELSE 0
            END
        )
            WHEN 1 THEN '白'
            WHEN 2 THEN '轻'
            WHEN 3 THEN '中'
            WHEN 4 THEN '重'
            ELSE NULL
        END::character varying AS "危害程度"
    FROM survey."国槐尺蠖幼虫调查表" AS c
    GROUP BY c."编号"
) AS l ON s."编号" = l."编号";

COMMENT ON VIEW views."2026_国槐尺蠖幼虫调查"
    IS '国槐尺蠖幼虫调查地图视图，仅保留核心点位与调查字段';

DROP VIEW IF EXISTS views."2026_春尺蠖幼虫调查";
CREATE VIEW views."2026_春尺蠖幼虫调查" AS
SELECT
    s.geom,
    s."编号",
    s."属地",
    NULLIF(BTRIM(s."村"), '') AS "点位名称",
    l."调查日期",
    l."危害程度"
FROM sites."杨树点位基础表" AS s
LEFT JOIN (
    SELECT
        c."编号",
        max(c."调查日期") AS "调查日期",
        CASE max(
            CASE BTRIM(COALESCE(c."危害程度", ''))
                WHEN '白' THEN 1
                WHEN '无需防治' THEN 1
                WHEN '轻' THEN 2
                WHEN '中' THEN 3
                WHEN '重' THEN 4
                ELSE 0
            END
        )
            WHEN 1 THEN '白'
            WHEN 2 THEN '轻'
            WHEN 3 THEN '中'
            WHEN 4 THEN '重'
            ELSE NULL
        END::character varying AS "危害程度"
    FROM survey."春尺蠖幼虫调查表" AS c
    GROUP BY c."编号"
) AS l ON s."编号" = l."编号"
WHERE s."春尺蠖_2026年成虫发生情况" <> '伐';

COMMENT ON VIEW views."2026_春尺蠖幼虫调查"
    IS '春尺蠖幼虫调查地图视图，仅保留核心点位与调查字段';

DROP VIEW IF EXISTS views."2026_春尺蠖成虫调查";
CREATE VIEW views."2026_春尺蠖成虫调查" AS
SELECT
    s.geom,
    s."编号",
    s."属地",
    NULLIF(BTRIM(s."村"), '') AS "点位名称",
    a."调查日期",
    a."危害程度"
FROM sites."杨树点位基础表" AS s
LEFT JOIN (
    SELECT
        c."编号",
        max(c."调查日期") AS "调查日期",
        CASE max(
            CASE BTRIM(COALESCE(c."受害程度", ''))
                WHEN '白' THEN 1
                WHEN '无需防治' THEN 1
                WHEN '轻' THEN 2
                WHEN '中' THEN 3
                WHEN '重' THEN 4
                ELSE 0
            END
        )
            WHEN 1 THEN '白'
            WHEN 2 THEN '轻'
            WHEN 3 THEN '中'
            WHEN 4 THEN '重'
            ELSE NULL
        END::character varying AS "危害程度"
    FROM survey."春尺蠖成虫调查表" AS c
    GROUP BY c."编号"
) AS a ON s."编号" = a."编号"
WHERE s."春尺蠖_2026年_围环发生情况" = '可调查';

COMMENT ON VIEW views."2026_春尺蠖成虫调查"
    IS '春尺蠖成虫调查地图视图，仅保留核心点位与调查字段';

DROP VIEW IF EXISTS views."2026_美国白蛾第 1 代调查";
CREATE VIEW views."2026_美国白蛾第 1 代调查" AS
WITH latest_inspection AS (
    SELECT DISTINCT ON (i."编号")
        BTRIM(i."编号") AS "编号",
        i."调查日期"
    FROM survey."美国白蛾第一代调查表" AS i
    WHERE BTRIM(COALESCE(i."编号", '')) <> ''
    ORDER BY i."编号", i."调查日期" DESC
)
SELECT
    c.geom,
    BTRIM(c."点位编号") AS "编号",
    NULLIF(BTRIM(c."属地"), '') AS "属地",
    NULLIF(BTRIM(c."点位名称"), '') AS "点位名称",
    l."调查日期"
FROM reference."通州区小区边界" AS c
LEFT JOIN latest_inspection AS l
  ON l."编号" = BTRIM(c."点位编号");

COMMENT ON VIEW views."2026_美国白蛾第 1 代调查"
    IS '美国白蛾第一代调查地图视图，仅保留核心点位与调查字段';

DROP VIEW IF EXISTS views."国槐尺蠖幼虫历年发生情况";
CREATE VIEW views."国槐尺蠖幼虫历年发生情况" AS
SELECT
    s.geom,
    s."编号",
    s."属地",
    NULLIF(BTRIM(s."村"), '') AS "点位名称",
    h."年份",
    NULLIF(BTRIM(h."发生情况"), '')::character varying AS "危害程度"
FROM sites."国槐点位基础表" AS s
CROSS JOIN LATERAL (
    VALUES
        ('2024'::text, s."国槐尺蠖_2024年_幼虫发生情况"::text),
        ('2025'::text, s."国槐尺蠖_2025年_幼虫发生情况"::text),
        ('2026'::text, s."国槐尺蠖_2026年_幼虫发生情况"::text)
) AS h("年份", "发生情况")
WHERE s.geom IS NOT NULL
  AND NULLIF(BTRIM(COALESCE(h."发生情况", '')), '') IS NOT NULL;

COMMENT ON VIEW views."国槐尺蠖幼虫历年发生情况"
    IS '国槐尺蠖幼虫历年发生情况地图视图，仅保留核心点位与年份危害字段';

DROP VIEW IF EXISTS views."美国白蛾点位";
CREATE VIEW views."美国白蛾点位" AS
SELECT
    s.geom,
    BTRIM(s."编号") AS "编号",
    NULLIF(BTRIM(s."属地"), '') AS "属地",
    NULLIF(BTRIM(COALESCE(s."点位名称", '')), '') AS "点位名称"
FROM sites."美国白蛾点位基础表" AS s
WHERE s.geom IS NOT NULL;

COMMENT ON VIEW views."美国白蛾点位"
    IS '美国白蛾基础点位地图视图，仅保留核心点位字段';

COMMIT;
