-- 阶段2迁移：重建 ledger 台账视图
-- 台账视图引用新表名（去年度/世代后缀），加年份/世代列
-- 前置条件：20260705_01_schema_migration.sql 已执行

BEGIN;

-- 旧台账视图已在 20260705_01_schema_migration.sql 中 DROP

-- ============================================================
-- 1. 美国白蛾问题点位台账
-- ============================================================
CREATE OR REPLACE VIEW ledger."美国白蛾问题点位台账" AS
WITH base_events AS (
    SELECT
        e.id,
        e."事件时间",
        e."事件类型",
        e."区域",
        e."属地",
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
        e."年份",
        e."世代",
        concat(EXTRACT(year FROM e."事件时间")::integer, '/', EXTRACT(month FROM e."事件时间")::integer, '/', EXTRACT(day FROM e."事件时间")::integer) AS event_date_text
    FROM ledger."美国白蛾问题点位事件流水表" e
), first_info AS (
    SELECT DISTINCT ON (b."编号", b."年份", b."世代")
        b."编号",
        b."区域",
        b."属地",
        b."点位名称",
        b."发生位置",
        b."绿地性质",
        b."危害寄主",
        b."年份",
        b."世代"
    FROM base_events b
    ORDER BY b."编号", b."年份", b."世代", b."事件时间", b.id
), last_event AS (
    SELECT DISTINCT ON (b."编号", b."年份", b."世代")
        b."编号",
        b."年份",
        b."世代",
        b."事件类型"::text AS last_event_type
    FROM base_events b
    ORDER BY b."编号", b."年份", b."世代", b."事件时间" DESC, b.id DESC
), first_dispatch_metrics AS (
    SELECT DISTINCT ON (b."编号", b."年份", b."世代")
        b."编号",
        b."年份",
        b."世代",
        COALESCE(b."受害株数", 0) AS "受害株数汇总",
        COALESCE(b."网幕数量", 0) AS "网幕数量汇总"
    FROM base_events b
    WHERE b."事件类型"::text = '调查下派'
    ORDER BY b."编号", b."年份", b."世代", b."事件时间", b.id
), dispatch_dates AS (
    SELECT
        d."编号",
        d."年份",
        d."世代",
        string_agg(d.event_date_text, '、' ORDER BY d.event_date) AS "下派日期列表"
    FROM (
        SELECT DISTINCT
            b."编号",
            b."年份",
            b."世代",
            b."事件时间"::date AS event_date,
            b.event_date_text
        FROM base_events b
        WHERE b."事件类型"::text = ANY (ARRAY['调查下派', '复查异常'])
    ) d
    GROUP BY d."编号", d."年份", d."世代"
), survey_dates AS (
    SELECT
        d."编号",
        d."年份",
        d."世代",
        string_agg(d.event_date_text, '、' ORDER BY d.event_date) AS "调查日期列表"
    FROM (
        SELECT DISTINCT
            b."编号",
            b."年份",
            b."世代",
            b."事件时间"::date AS event_date,
            b.event_date_text
        FROM base_events b
        WHERE b."事件类型"::text = ANY (ARRAY['调查下派', '复查异常', '复查合格'])
    ) d
    GROUP BY d."编号", d."年份", d."世代"
), treatment_dates AS (
    SELECT
        d."编号",
        d."年份",
        d."世代",
        string_agg(d.event_date_text, '、' ORDER BY d.event_date) AS "防治日期列表"
    FROM (
        SELECT DISTINCT
            b."编号",
            b."年份",
            b."世代",
            b."事件时间"::date AS event_date,
            b.event_date_text
        FROM base_events b
        WHERE b."事件类型"::text = '防治'
    ) d
    GROUP BY d."编号", d."年份", d."世代"
), event_agg AS (
    SELECT
        b."编号",
        b."年份",
        b."世代",
        count(*) FILTER (WHERE b."事件类型"::text = ANY (ARRAY['调查下派', '复查异常']))::integer AS "下派次数",
        count(*) FILTER (WHERE b."事件类型"::text = ANY (ARRAY['调查下派', '复查异常', '复查合格']))::integer AS "调查次数",
        count(*) FILTER (WHERE b."事件类型"::text = '防治')::integer AS "防治次数",
        max(
            CASE
                WHEN b."是否剪网"::text = '是' THEN 2
                WHEN b."是否剪网"::text = '否' THEN 1
                ELSE 0
            END
        ) AS pruning_rank,
        max(
            CASE
                WHEN b."是否剪网"::text = '是' AND b."剪网彻底"::text = '否' THEN 2
                WHEN b."是否剪网"::text = '是' AND b."剪网彻底"::text = '是' THEN 1
                WHEN b."是否剪网"::text = '否' OR b."剪网彻底"::text = '不涉及' THEN 0
                ELSE NULL
            END
        ) AS pruning_complete_rank,
        string_agg(
            CASE
                WHEN BTRIM(COALESCE(b."本次详细情况", '')) <> '' THEN
                    ((b.event_date_text || ' ') || b."事件类型") || '：' || b."本次详细情况"
                ELSE
                    (b.event_date_text || ' ') || b."事件类型"
            END, '；' ORDER BY b."事件时间", b.id
        ) AS "详细情况",
        string_agg(DISTINCT
            CASE
                WHEN BTRIM(COALESCE(b."备注", '')) <> '' THEN b."备注"
                ELSE NULL
            END, '、'
        ) FILTER (WHERE BTRIM(COALESCE(b."备注", '')) <> '') AS "备注"
    FROM base_events b
    GROUP BY b."编号", b."年份", b."世代"
)
SELECT
    f."编号",
    f."区域",
    f."属地",
    f."点位名称",
    f."发生位置",
    f."绿地性质",
    f."危害寄主",
    f."年份",
    f."世代",
    COALESCE(fdm."受害株数汇总", 0) AS "受害株数汇总",
    COALESCE(fdm."网幕数量汇总", 0) AS "网幕数量汇总",
    COALESCE(dd."下派日期列表", '') AS "下派日期列表",
    a."下派次数",
    COALESCE(sd."调查日期列表", '') AS "调查日期列表",
    a."调查次数",
    COALESCE(td."防治日期列表", '') AS "防治日期列表",
    a."防治次数",
    CASE a.pruning_rank
        WHEN 2 THEN '是' WHEN 1 THEN '否' ELSE NULL
    END::character varying AS "是否剪网",
    CASE a.pruning_complete_rank
        WHEN 2 THEN '否' WHEN 1 THEN '是' WHEN 0 THEN '不涉及' ELSE NULL
    END::character varying AS "剪网彻底",
    a."详细情况",
    CASE le.last_event_type
        WHEN '调查下派' THEN '待防治'
        WHEN '防治' THEN '待复查'
        WHEN '复查异常' THEN '复查异常'
        WHEN '复查合格' THEN '已闭环'
        ELSE NULL
    END::character varying AS "当前状态",
    a."备注"
FROM first_info f
JOIN event_agg a ON a."编号" = f."编号" AND a."年份" = f."年份" AND a."世代" = f."世代"
JOIN last_event le ON le."编号" = f."编号" AND le."年份" = f."年份" AND le."世代" = f."世代"
LEFT JOIN first_dispatch_metrics fdm ON fdm."编号" = f."编号" AND fdm."年份" = f."年份" AND fdm."世代" = f."世代"
LEFT JOIN dispatch_dates dd ON dd."编号" = f."编号" AND dd."年份" = f."年份" AND dd."世代" = f."世代"
LEFT JOIN survey_dates sd ON sd."编号" = f."编号" AND sd."年份" = f."年份" AND sd."世代" = f."世代"
LEFT JOIN treatment_dates td ON td."编号" = f."编号" AND td."年份" = f."年份" AND td."世代" = f."世代"
ORDER BY f."编号";

-- ============================================================
-- 2. 国槐尺蠖问题点位台账
-- ============================================================
CREATE OR REPLACE VIEW ledger."国槐尺蠖问题点位台账" AS
WITH base_events AS (
    SELECT
        e.id,
        e."事件时间",
        e."事件类型",
        e."属地",
        e."编号",
        e."点位名称",
        e."本次平均虫口数",
        e."本次危害程度",
        e."本次详细情况",
        e."备注",
        e."年份",
        e."世代",
        concat(EXTRACT(year FROM e."事件时间")::integer, '/', EXTRACT(month FROM e."事件时间")::integer, '/', EXTRACT(day FROM e."事件时间")::integer) AS event_date_text
    FROM ledger."国槐尺蠖问题点位事件流水表" e
), first_info AS (
    SELECT DISTINCT ON (b."编号", b."年份", b."世代")
        b."编号",
        b."属地",
        b."点位名称",
        b."年份",
        b."世代"
    FROM base_events b
    ORDER BY b."编号", b."年份", b."世代", b."事件时间", b.id
), last_event AS (
    SELECT DISTINCT ON (b."编号", b."年份", b."世代")
        b."编号",
        b."年份",
        b."世代",
        b."事件类型"::text AS last_event_type
    FROM base_events b
    ORDER BY b."编号", b."年份", b."世代", b."事件时间" DESC, b.id DESC
), dispatch_dates AS (
    SELECT
        d."编号", d."年份", d."世代",
        string_agg(d.event_date_text, '、' ORDER BY d.event_date) AS "下派日期列表"
    FROM (
        SELECT DISTINCT b."编号", b."年份", b."世代", b."事件时间"::date AS event_date, b.event_date_text
        FROM base_events b
        WHERE b."事件类型"::text = ANY (ARRAY['历史预警下派', '幼虫调查下派', '复查异常'])
    ) d
    GROUP BY d."编号", d."年份", d."世代"
), survey_dates AS (
    SELECT
        d."编号", d."年份", d."世代",
        string_agg(d.event_date_text, '、' ORDER BY d.event_date) AS "调查日期列表"
    FROM (
        SELECT DISTINCT b."编号", b."年份", b."世代", b."事件时间"::date AS event_date, b.event_date_text
        FROM base_events b
        WHERE b."事件类型"::text = ANY (ARRAY['幼虫调查下派', '复查异常', '复查合格'])
    ) d
    GROUP BY d."编号", d."年份", d."世代"
), treatment_dates AS (
    SELECT
        d."编号", d."年份", d."世代",
        string_agg(d.event_date_text, '、' ORDER BY d.event_date) AS "防治日期列表"
    FROM (
        SELECT DISTINCT b."编号", b."年份", b."世代", b."事件时间"::date AS event_date, b.event_date_text
        FROM base_events b
        WHERE b."事件类型"::text = '防治'
    ) d
    GROUP BY d."编号", d."年份", d."世代"
), event_agg AS (
    SELECT
        b."编号", b."年份", b."世代",
        count(*) FILTER (WHERE b."事件类型"::text = ANY (ARRAY['历史预警下派', '幼虫调查下派', '复查异常']))::integer AS "下派次数",
        count(*) FILTER (WHERE b."事件类型"::text = ANY (ARRAY['幼虫调查下派', '复查异常', '复查合格']))::integer AS "调查次数",
        count(*) FILTER (WHERE b."事件类型"::text = '防治')::integer AS "防治次数",
        COALESCE(sum(COALESCE(b."本次平均虫口数", 0)) FILTER (WHERE b."事件类型"::text = ANY (ARRAY['幼虫调查下派', '复查异常', '复查合格'])), 0::bigint)::integer AS "平均虫口数汇总",
        max(
            CASE
                WHEN b."事件类型"::text = ANY (ARRAY['幼虫调查下派', '复查异常', '复查合格']) THEN
                    CASE b."本次危害程度"
                        WHEN '白' THEN 1 WHEN '轻' THEN 2 WHEN '中' THEN 3 WHEN '重' THEN 4 ELSE 0
                    END
                ELSE NULL
            END
        ) AS max_damage_rank,
        string_agg(
            CASE
                WHEN BTRIM(COALESCE(b."本次详细情况", '')) <> '' THEN
                    ((b.event_date_text || ' ') || b."事件类型") || '：' || b."本次详细情况"
                ELSE
                    (b.event_date_text || ' ') || b."事件类型"
            END, '；' ORDER BY b."事件时间", b.id
        ) AS "详细情况"
    FROM base_events b
    GROUP BY b."编号", b."年份", b."世代"
)
SELECT
    f."编号",
    f."属地",
    f."点位名称",
    f."年份",
    f."世代",
    COALESCE(dd."下派日期列表", '') AS "下派日期列表",
    a."下派次数",
    COALESCE(sd."调查日期列表", '') AS "调查日期列表",
    a."调查次数",
    COALESCE(td."防治日期列表", '') AS "防治日期列表",
    a."防治次数",
    a."平均虫口数汇总",
    CASE a.max_damage_rank
        WHEN 1 THEN '白' WHEN 2 THEN '轻' WHEN 3 THEN '中' WHEN 4 THEN '重' ELSE NULL
    END::character varying AS "危害程度",
    a."详细情况",
    CASE le.last_event_type
        WHEN '历史预警下派' THEN '待防治'
        WHEN '幼虫调查下派' THEN '待防治'
        WHEN '防治' THEN '待复查'
        WHEN '复查异常' THEN '复查异常'
        WHEN '复查合格' THEN '已闭环'
        ELSE NULL
    END::character varying AS "当前状态"
FROM first_info f
JOIN event_agg a ON a."编号" = f."编号" AND a."年份" = f."年份" AND a."世代" = f."世代"
JOIN last_event le ON le."编号" = f."编号" AND le."年份" = f."年份" AND le."世代" = f."世代"
LEFT JOIN dispatch_dates dd ON dd."编号" = f."编号" AND dd."年份" = f."年份" AND dd."世代" = f."世代"
LEFT JOIN survey_dates sd ON sd."编号" = f."编号" AND sd."年份" = f."年份" AND sd."世代" = f."世代"
LEFT JOIN treatment_dates td ON td."编号" = f."编号" AND td."年份" = f."年份" AND td."世代" = f."世代";

-- ============================================================
-- 3. 春尺蠖问题点位台账
-- ============================================================
CREATE OR REPLACE VIEW ledger."春尺蠖问题点位台账" AS
WITH base_events AS (
    SELECT
        e.id,
        e."事件时间",
        e."事件类型",
        e."属地",
        e."编号",
        e."点位名称",
        e."本次平均虫口数",
        e."本次危害程度",
        e."本次详细情况",
        e."备注",
        e."年份",
        concat(EXTRACT(year FROM e."事件时间")::integer, '/', EXTRACT(month FROM e."事件时间")::integer, '/', EXTRACT(day FROM e."事件时间")::integer) AS event_date_text
    FROM ledger."春尺蠖问题点位事件流水表" e
), first_info AS (
    SELECT DISTINCT ON (b."编号", b."年份")
        b."编号", b."属地", b."点位名称", b."年份"
    FROM base_events b
    ORDER BY b."编号", b."年份", b."事件时间", b.id
), last_event AS (
    SELECT DISTINCT ON (b."编号", b."年份")
        b."编号", b."年份", b."事件类型"::text AS last_event_type
    FROM base_events b
    ORDER BY b."编号", b."年份", b."事件时间" DESC, b.id DESC
), dispatch_dates AS (
    SELECT
        d."编号", d."年份",
        string_agg(d.event_date_text, '、' ORDER BY d.event_date) AS "下派日期列表"
    FROM (
        SELECT DISTINCT b."编号", b."年份", b."事件时间"::date AS event_date, b.event_date_text
        FROM base_events b
        WHERE b."事件类型"::text = ANY (ARRAY['历史预警下派', '幼虫调查下派', '成虫调查下派', '复查异常'])
    ) d
    GROUP BY d."编号", d."年份"
), survey_dates AS (
    SELECT
        d."编号", d."年份",
        string_agg(d.event_date_text, '、' ORDER BY d.event_date) AS "调查日期列表"
    FROM (
        SELECT DISTINCT b."编号", b."年份", b."事件时间"::date AS event_date, b.event_date_text
        FROM base_events b
        WHERE b."事件类型"::text = ANY (ARRAY['幼虫调查下派', '成虫调查下派', '复查异常', '复查合格'])
    ) d
    GROUP BY d."编号", d."年份"
), treatment_dates AS (
    SELECT
        d."编号", d."年份",
        string_agg(d.event_date_text, '、' ORDER BY d.event_date) AS "防治日期列表"
    FROM (
        SELECT DISTINCT b."编号", b."年份", b."事件时间"::date AS event_date, b.event_date_text
        FROM base_events b
        WHERE b."事件类型"::text = '防治'
    ) d
    GROUP BY d."编号", d."年份"
), event_agg AS (
    SELECT
        b."编号", b."年份",
        count(*) FILTER (WHERE b."事件类型"::text = ANY (ARRAY['历史预警下派', '幼虫调查下派', '成虫调查下派', '复查异常']))::integer AS "下派次数",
        count(*) FILTER (WHERE b."事件类型"::text = ANY (ARRAY['幼虫调查下派', '成虫调查下派', '复查异常', '复查合格']))::integer AS "调查次数",
        count(*) FILTER (WHERE b."事件类型"::text = '防治')::integer AS "防治次数",
        COALESCE(sum(COALESCE(b."本次平均虫口数", 0)) FILTER (WHERE b."事件类型"::text = ANY (ARRAY['幼虫调查下派', '成虫调查下派', '复查异常', '复查合格'])), 0::bigint)::integer AS "平均虫口数汇总",
        max(
            CASE
                WHEN b."事件类型"::text = ANY (ARRAY['幼虫调查下派', '成虫调查下派', '复查异常', '复查合格']) THEN
                    CASE b."本次危害程度"
                        WHEN '白' THEN 1 WHEN '轻' THEN 2 WHEN '中' THEN 3 WHEN '重' THEN 4 ELSE 0
                    END
                ELSE NULL
            END
        ) AS max_damage_rank,
        string_agg(
            CASE
                WHEN BTRIM(COALESCE(b."本次详细情况", '')) <> '' THEN
                    ((b.event_date_text || ' ') || b."事件类型") || '：' || b."本次详细情况"
                ELSE
                    (b.event_date_text || ' ') || b."事件类型"
            END, '；' ORDER BY b."事件时间", b.id
        ) AS "详细情况"
    FROM base_events b
    GROUP BY b."编号", b."年份"
)
SELECT
    f."编号", f."属地", f."点位名称", f."年份",
    COALESCE(dd."下派日期列表", '') AS "下派日期列表",
    a."下派次数",
    COALESCE(sd."调查日期列表", '') AS "调查日期列表",
    a."调查次数",
    COALESCE(td."防治日期列表", '') AS "防治日期列表",
    a."防治次数",
    a."平均虫口数汇总",
    CASE a.max_damage_rank
        WHEN 1 THEN '白' WHEN 2 THEN '轻' WHEN 3 THEN '中' WHEN 4 THEN '重' ELSE NULL
    END::character varying AS "危害程度",
    a."详细情况",
    CASE le.last_event_type
        WHEN '历史预警下派' THEN '待防治'
        WHEN '幼虫调查下派' THEN '待防治'
        WHEN '成虫调查下派' THEN '待防治'
        WHEN '防治' THEN '待复查'
        WHEN '复查异常' THEN '复查异常'
        WHEN '复查合格' THEN '已闭环'
        ELSE NULL
    END::character varying AS "当前状态"
FROM first_info f
JOIN event_agg a ON a."编号" = f."编号" AND a."年份" = f."年份"
JOIN last_event le ON le."编号" = f."编号" AND le."年份" = f."年份"
LEFT JOIN dispatch_dates dd ON dd."编号" = f."编号" AND dd."年份" = f."年份"
LEFT JOIN survey_dates sd ON sd."编号" = f."编号" AND sd."年份" = f."年份"
LEFT JOIN treatment_dates td ON td."编号" = f."编号" AND td."年份" = f."年份";

-- ============================================================
-- 4. 其他害虫问题点位台账
-- ============================================================
CREATE OR REPLACE VIEW ledger."其他害虫问题点位台账" AS
WITH base_events AS (
    SELECT
        e.id,
        e."事件时间",
        e."事件类型",
        e."虫害类型",
        e."属地",
        e."编号",
        e."点位名称",
        e."寄主树种",
        e."本次调查结论",
        e."本次详细情况",
        e."备注",
        e."年份",
        concat(EXTRACT(year FROM e."事件时间")::integer, '/', EXTRACT(month FROM e."事件时间")::integer, '/', EXTRACT(day FROM e."事件时间")::integer) AS event_date_text
    FROM ledger."其他害虫问题点位事件流水表" e
), first_info AS (
    SELECT DISTINCT ON (b."编号", b."虫害类型", b."年份")
        b."编号", b."虫害类型", b."属地", b."点位名称", b."寄主树种", b."年份"
    FROM base_events b
    ORDER BY b."编号", b."虫害类型", b."年份", b."事件时间", b.id
), last_event AS (
    SELECT DISTINCT ON (b."编号", b."虫害类型", b."年份")
        b."编号", b."虫害类型", b."年份", b."事件类型"::text AS last_event_type
    FROM base_events b
    ORDER BY b."编号", b."虫害类型", b."年份", b."事件时间" DESC, b.id DESC
), dispatch_dates AS (
    SELECT
        d."编号", d."虫害类型", d."年份",
        string_agg(d.event_date_text, '、' ORDER BY d.event_date) AS "下派日期列表"
    FROM (
        SELECT DISTINCT b."编号", b."虫害类型", b."年份", b."事件时间"::date AS event_date, b.event_date_text
        FROM base_events b
        WHERE b."事件类型"::text = ANY (ARRAY['调查下派', '复查异常'])
    ) d
    GROUP BY d."编号", d."虫害类型", d."年份"
), survey_dates AS (
    SELECT
        d."编号", d."虫害类型", d."年份",
        string_agg(d.event_date_text, '、' ORDER BY d.event_date) AS "调查日期列表"
    FROM (
        SELECT DISTINCT b."编号", b."虫害类型", b."年份", b."事件时间"::date AS event_date, b.event_date_text
        FROM base_events b
        WHERE b."本次调查结论" IS NOT NULL
    ) d
    GROUP BY d."编号", d."虫害类型", d."年份"
), treatment_dates AS (
    SELECT
        d."编号", d."虫害类型", d."年份",
        string_agg(d.event_date_text, '、' ORDER BY d.event_date) AS "防治日期列表"
    FROM (
        SELECT DISTINCT b."编号", b."虫害类型", b."年份", b."事件时间"::date AS event_date, b.event_date_text
        FROM base_events b
        WHERE b."事件类型"::text = '防治'
    ) d
    GROUP BY d."编号", d."虫害类型", d."年份"
), detail_agg AS (
    SELECT
        b."编号", b."虫害类型", b."年份",
        string_agg(
            CASE
                WHEN BTRIM(COALESCE(b."本次详细情况", '')) <> '' THEN
                    ((b.event_date_text || ' ') || b."事件类型") || '：' || b."本次详细情况"
                ELSE
                    (b.event_date_text || ' ') || b."事件类型"
            END, '；' ORDER BY b."事件时间", b.id
        ) AS "详细情况"
    FROM base_events b
    GROUP BY b."编号", b."虫害类型", b."年份"
)
SELECT
    f."编号", f."虫害类型", f."属地", f."点位名称", f."寄主树种", f."年份",
    COALESCE(dd."下派日期列表", '') AS "下派日期列表",
    COALESCE(sd."调查日期列表", '') AS "调查日期列表",
    COALESCE(td."防治日期列表", '') AS "防治日期列表",
    da."详细情况",
    CASE le.last_event_type
        WHEN '调查下派' THEN '待防治'
        WHEN '防治' THEN '待复查'
        WHEN '复查异常' THEN '复查异常'
        WHEN '复查合格' THEN '已闭环'
        ELSE NULL
    END::character varying AS "当前状态"
FROM first_info f
JOIN last_event le ON le."编号" = f."编号" AND le."虫害类型" = f."虫害类型" AND le."年份" = f."年份"
LEFT JOIN dispatch_dates dd ON dd."编号" = f."编号" AND dd."虫害类型" = f."虫害类型" AND dd."年份" = f."年份"
LEFT JOIN survey_dates sd ON sd."编号" = f."编号" AND sd."虫害类型" = f."虫害类型" AND sd."年份" = f."年份"
LEFT JOIN treatment_dates td ON td."编号" = f."编号" AND td."虫害类型" = f."虫害类型" AND td."年份" = f."年份"
JOIN detail_agg da ON da."编号" = f."编号" AND da."虫害类型" = f."虫害类型" AND da."年份" = f."年份";

COMMIT;
