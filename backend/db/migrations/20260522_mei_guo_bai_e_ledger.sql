CREATE SCHEMA IF NOT EXISTS survey;
CREATE SCHEMA IF NOT EXISTS ledger;

DO $$
DECLARE
    old_constraint_names text[] := ARRAY[
        'mei_guo_bai_e_inspection_pkey',
        'mei_guo_bai_e_inspection_damaged_plant_count_check',
        'mei_guo_bai_e_inspection_web_nest_count_check',
        'mei_guo_bai_e_inspection_pruning_status_check',
        'mei_guo_bai_e_inspection_pruning_complete_check',
        'mei_guo_bai_e_inspection_pruning_consistency_check'
    ];
    new_constraint_names text[] := ARRAY[
        'mgb1_inspection_pkey',
        'mgb1_damaged_plant_count_check',
        'mgb1_web_nest_count_check',
        'mgb1_pruning_status_check',
        'mgb1_pruning_complete_check',
        'mgb1_pruning_consistency_check'
    ];
    constraint_index integer;
BEGIN
    IF to_regclass('survey.mei_guo_bai_e_inspection') IS NOT NULL
       AND to_regclass('survey.mei_guo_bai_e_first_generation_inspection') IS NULL THEN
        ALTER TABLE survey.mei_guo_bai_e_inspection
            RENAME TO mei_guo_bai_e_first_generation_inspection;
    END IF;

    FOR constraint_index IN 1..array_length(old_constraint_names, 1) LOOP
        IF EXISTS (
            SELECT 1
            FROM pg_constraint
            WHERE conrelid = 'survey.mei_guo_bai_e_first_generation_inspection'::regclass
              AND conname = old_constraint_names[constraint_index]
        )
        AND NOT EXISTS (
            SELECT 1
            FROM pg_constraint
            WHERE conrelid = 'survey.mei_guo_bai_e_first_generation_inspection'::regclass
              AND conname = new_constraint_names[constraint_index]
        ) THEN
            EXECUTE format(
                'ALTER TABLE survey.mei_guo_bai_e_first_generation_inspection RENAME CONSTRAINT %I TO %I',
                old_constraint_names[constraint_index],
                new_constraint_names[constraint_index]
            );
        END IF;
    END LOOP;
END $$;

COMMENT ON TABLE survey.mei_guo_bai_e_first_generation_inspection
    IS '美国白蛾第一代巡查表';

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1
        FROM pg_type t
        JOIN pg_namespace n ON n.oid = t.typnamespace
        WHERE n.nspname = 'ledger'
          AND t.typname = 'meiguobaie_event_type'
    ) THEN
        CREATE TYPE ledger.meiguobaie_event_type AS ENUM (
            '调查下派',
            '防治',
            '复查异常',
            '复查合格'
        );
    END IF;
END $$;

CREATE TABLE IF NOT EXISTS ledger."2026年美国白蛾第一代问题点位事件流水表" (
    id integer NOT NULL,
    "事件时间" timestamp without time zone NOT NULL,
    "事件类型" ledger.meiguobaie_event_type NOT NULL,
    "区域" character varying NOT NULL DEFAULT '乡镇',
    "乡镇" character varying,
    "编号" character varying NOT NULL,
    "点位名称" character varying,
    "发生位置" character varying,
    "绿地性质" character varying,
    "危害寄主" character varying,
    "受害株数" integer NOT NULL DEFAULT 0,
    "网幕数量" integer NOT NULL DEFAULT 0,
    "是否剪网" character varying,
    "剪网彻底" character varying,
    "本次详细情况" text NOT NULL,
    "备注" text,
    CONSTRAINT mgb1_ledger_pkey PRIMARY KEY (id),
    CONSTRAINT mgb1_ledger_region_check
        CHECK ("区域" IN ('城区', '乡镇')),
    CONSTRAINT mgb1_ledger_damaged_plant_count_check
        CHECK ("受害株数" >= 0),
    CONSTRAINT mgb1_ledger_web_nest_count_check
        CHECK ("网幕数量" >= 0),
    CONSTRAINT mgb1_ledger_pruning_status_check
        CHECK ("是否剪网" IS NULL OR "是否剪网" IN ('是', '否')),
    CONSTRAINT mgb1_ledger_pruning_complete_check
        CHECK ("剪网彻底" IS NULL OR "剪网彻底" IN ('是', '否', '不涉及')),
    CONSTRAINT mgb1_ledger_pruning_consistency_check
        CHECK (
            "是否剪网" IS NULL
            OR ("是否剪网" = '否' AND COALESCE("剪网彻底", '不涉及') = '不涉及')
            OR ("是否剪网" = '是' AND "剪网彻底" IN ('是', '否'))
        )
);

COMMENT ON TABLE ledger."2026年美国白蛾第一代问题点位事件流水表"
    IS '2026年美国白蛾第一代问题点位事件流水表';

COMMENT ON COLUMN ledger."2026年美国白蛾第一代问题点位事件流水表"."区域"
    IS '取值：城区、乡镇';

COMMENT ON COLUMN ledger."2026年美国白蛾第一代问题点位事件流水表"."本次详细情况"
    IS '由 survey.mei_guo_bai_e_first_generation_inspection."详细描述" 完整承接，不使用平均虫口数或危害程度生成';

INSERT INTO ledger."2026年美国白蛾第一代问题点位事件流水表" (
    id,
    "事件时间",
    "事件类型",
    "区域",
    "乡镇",
    "编号",
    "点位名称",
    "发生位置",
    "绿地性质",
    "危害寄主",
    "受害株数",
    "网幕数量",
    "是否剪网",
    "剪网彻底",
    "本次详细情况",
    "备注"
)
SELECT
    row_number() OVER (ORDER BY i."调查日期", i."编号")::integer AS id,
    i."调查日期"::timestamp without time zone AS "事件时间",
    '调查下派'::ledger.meiguobaie_event_type AS "事件类型",
    i."区域" AS "区域",
    NULLIF(BTRIM(i."乡镇"), '') AS "乡镇",
    BTRIM(i."编号") AS "编号",
    NULLIF(BTRIM(i."点位名称"), '') AS "点位名称",
    NULLIF(BTRIM(i."发生位置"), '') AS "发生位置",
    NULLIF(BTRIM(i."绿地性质"), '') AS "绿地性质",
    NULLIF(BTRIM(i."危害寄主"), '') AS "危害寄主",
    COALESCE(i."受害株数", 0) AS "受害株数",
    COALESCE(i."网幕数量", 0) AS "网幕数量",
    NULLIF(BTRIM(i."是否剪网"), '') AS "是否剪网",
    NULLIF(BTRIM(i."剪网彻底"), '') AS "剪网彻底",
    BTRIM(i."详细描述") AS "本次详细情况",
    CASE
        WHEN BTRIM(COALESCE(i."备注", '')) <> ''
            THEN '初始化导入；调查表备注：' || BTRIM(i."备注")
        ELSE '初始化导入'
    END AS "备注"
FROM survey.mei_guo_bai_e_first_generation_inspection AS i
WHERE BTRIM(COALESCE(i."详细描述", '')) <> ''
  AND NOT EXISTS (
      SELECT 1
      FROM ledger."2026年美国白蛾第一代问题点位事件流水表"
  )
ORDER BY i."调查日期", i."编号";
