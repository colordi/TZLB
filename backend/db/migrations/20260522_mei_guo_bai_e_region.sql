CREATE SCHEMA IF NOT EXISTS survey;
CREATE SCHEMA IF NOT EXISTS ledger;

ALTER TABLE survey.mei_guo_bai_e_first_generation_inspection
    ADD COLUMN IF NOT EXISTS "区域" character varying NOT NULL DEFAULT '乡镇';

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1
        FROM pg_constraint
        WHERE conrelid = 'survey.mei_guo_bai_e_first_generation_inspection'::regclass
          AND conname = 'mgb1_region_check'
    ) THEN
        ALTER TABLE survey.mei_guo_bai_e_first_generation_inspection
            ADD CONSTRAINT mgb1_region_check
            CHECK ("区域" IN ('城区', '乡镇'));
    END IF;
END $$;

COMMENT ON COLUMN survey.mei_guo_bai_e_first_generation_inspection."区域"
    IS '取值：城区、乡镇';

ALTER TABLE ledger."2026年美国白蛾第一代问题点位事件流水表"
    ADD COLUMN IF NOT EXISTS "区域" character varying NOT NULL DEFAULT '乡镇';

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1
        FROM pg_constraint
        WHERE conrelid = 'ledger."2026年美国白蛾第一代问题点位事件流水表"'::regclass
          AND conname = 'mgb1_ledger_region_check'
    ) THEN
        ALTER TABLE ledger."2026年美国白蛾第一代问题点位事件流水表"
            ADD CONSTRAINT mgb1_ledger_region_check
            CHECK ("区域" IN ('城区', '乡镇'));
    END IF;
END $$;

COMMENT ON COLUMN ledger."2026年美国白蛾第一代问题点位事件流水表"."区域"
    IS '取值：城区、乡镇';

DROP VIEW IF EXISTS ledger."2026年美国白蛾第一代问题点位台账";

CREATE VIEW ledger."2026年美国白蛾第一代问题点位台账" AS
WITH base_events AS (
    SELECT
        e.id,
        e."事件时间",
        e."事件类型",
        e."区域",
        e."乡镇",
        e."编号",
        e."点位名称",
        e."发生位置",
        e."绿地性质",
        e."危害寄主",
        e."受害株数",
        e."网幕数量",
        e."是否剪网",
        e."剪网彻底",
        e."本次详细情况",
        e."备注",
        concat(
            EXTRACT(year FROM e."事件时间")::integer,
            '/',
            EXTRACT(month FROM e."事件时间")::integer,
            '/',
            EXTRACT(day FROM e."事件时间")::integer
        ) AS event_date_text
    FROM ledger."2026年美国白蛾第一代问题点位事件流水表" AS e
),
first_info AS (
    SELECT DISTINCT ON (b."编号")
        b."编号",
        b."区域",
        b."乡镇",
        b."点位名称",
        b."发生位置",
        b."绿地性质",
        b."危害寄主"
    FROM base_events AS b
    ORDER BY b."编号", b."事件时间", b.id
),
last_event AS (
    SELECT DISTINCT ON (b."编号")
        b."编号",
        b."事件类型"::text AS last_event_type
    FROM base_events AS b
    ORDER BY b."编号", b."事件时间" DESC, b.id DESC
),
dispatch_dates AS (
    SELECT
        d."编号",
        string_agg(d.event_date_text, '、' ORDER BY d.event_date) AS "下派日期列表"
    FROM (
        SELECT DISTINCT
            b."编号",
            b."事件时间"::date AS event_date,
            b.event_date_text
        FROM base_events AS b
        WHERE b."事件类型"::text IN ('调查下派', '复查异常')
    ) AS d
    GROUP BY d."编号"
),
survey_dates AS (
    SELECT
        d."编号",
        string_agg(d.event_date_text, '、' ORDER BY d.event_date) AS "调查日期列表"
    FROM (
        SELECT DISTINCT
            b."编号",
            b."事件时间"::date AS event_date,
            b.event_date_text
        FROM base_events AS b
        WHERE b."事件类型"::text IN ('调查下派', '复查异常', '复查合格')
    ) AS d
    GROUP BY d."编号"
),
treatment_dates AS (
    SELECT
        d."编号",
        string_agg(d.event_date_text, '、' ORDER BY d.event_date) AS "防治日期列表"
    FROM (
        SELECT DISTINCT
            b."编号",
            b."事件时间"::date AS event_date,
            b.event_date_text
        FROM base_events AS b
        WHERE b."事件类型"::text = '防治'
    ) AS d
    GROUP BY d."编号"
),
event_agg AS (
    SELECT
        b."编号",
        count(*) FILTER (
            WHERE b."事件类型"::text IN ('调查下派', '复查异常')
        )::integer AS "下派次数",
        count(*) FILTER (
            WHERE b."事件类型"::text IN ('调查下派', '复查异常', '复查合格')
        )::integer AS "调查次数",
        count(*) FILTER (
            WHERE b."事件类型"::text = '防治'
        )::integer AS "防治次数",
        COALESCE(
            sum(COALESCE(b."受害株数", 0)) FILTER (
                WHERE b."事件类型"::text IN ('调查下派', '复查异常', '复查合格')
            ),
            0
        )::integer AS "受害株数汇总",
        COALESCE(
            sum(COALESCE(b."网幕数量", 0)) FILTER (
                WHERE b."事件类型"::text IN ('调查下派', '复查异常', '复查合格')
            ),
            0
        )::integer AS "网幕数量汇总",
        max(
            CASE
                WHEN b."是否剪网" = '是' THEN 2
                WHEN b."是否剪网" = '否' THEN 1
                ELSE 0
            END
        ) AS pruning_rank,
        max(
            CASE
                WHEN b."是否剪网" = '是' AND b."剪网彻底" = '否' THEN 2
                WHEN b."是否剪网" = '是' AND b."剪网彻底" = '是' THEN 1
                WHEN b."是否剪网" = '否' OR b."剪网彻底" = '不涉及' THEN 0
                ELSE NULL
            END
        ) AS pruning_complete_rank,
        string_agg(
            CASE
                WHEN BTRIM(COALESCE(b."本次详细情况", '')) <> ''
                    THEN b.event_date_text || ' ' || b."事件类型"::text || '：' || b."本次详细情况"
                ELSE b.event_date_text || ' ' || b."事件类型"::text
            END,
            '；'
            ORDER BY b."事件时间", b.id
        ) AS "详细情况"
    FROM base_events AS b
    GROUP BY b."编号"
)
SELECT
    f."编号",
    f."区域",
    f."乡镇",
    f."点位名称",
    f."发生位置",
    f."绿地性质",
    f."危害寄主",
    COALESCE(dd."下派日期列表", '') AS "下派日期列表",
    a."下派次数",
    COALESCE(sd."调查日期列表", '') AS "调查日期列表",
    a."调查次数",
    COALESCE(td."防治日期列表", '') AS "防治日期列表",
    a."防治次数",
    a."受害株数汇总",
    a."网幕数量汇总",
    CASE a.pruning_rank
        WHEN 2 THEN '是'
        WHEN 1 THEN '否'
        ELSE NULL
    END::character varying AS "是否剪网",
    CASE a.pruning_complete_rank
        WHEN 2 THEN '否'
        WHEN 1 THEN '是'
        WHEN 0 THEN '不涉及'
        ELSE NULL
    END::character varying AS "剪网彻底",
    a."详细情况",
    CASE le.last_event_type
        WHEN '调查下派' THEN '待防治'
        WHEN '防治' THEN '待复查'
        WHEN '复查异常' THEN '复查异常'
        WHEN '复查合格' THEN '已闭环'
        ELSE NULL
    END::character varying AS "当前状态"
FROM first_info AS f
JOIN event_agg AS a
  ON a."编号"::text = f."编号"::text
JOIN last_event AS le
  ON le."编号"::text = f."编号"::text
LEFT JOIN dispatch_dates AS dd
  ON dd."编号"::text = f."编号"::text
LEFT JOIN survey_dates AS sd
  ON sd."编号"::text = f."编号"::text
LEFT JOIN treatment_dates AS td
  ON td."编号"::text = f."编号"::text;

COMMENT ON VIEW ledger."2026年美国白蛾第一代问题点位台账"
    IS '2026年美国白蛾第一代问题点位台账，由事件流水表聚合生成';
