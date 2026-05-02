CREATE SCHEMA IF NOT EXISTS survey;
CREATE SCHEMA IF NOT EXISTS views;

CREATE TABLE IF NOT EXISTS survey.guo_huai_chi_huo_larva (
    "编号" character varying NOT NULL,
    "调查日期" date NOT NULL,
    "1号树" integer DEFAULT 0,
    "2号树" integer DEFAULT 0,
    "3号树" integer DEFAULT 0,
    "4号树" integer DEFAULT 0,
    "5号树" integer DEFAULT 0,
    "总虫口数" integer,
    "备注" text,
    "危害程度" character varying,
    "平均虫口数" integer,
    CONSTRAINT guo_huai_chi_huo_larva_pkey PRIMARY KEY ("编号", "调查日期")
);

DROP TRIGGER IF EXISTS trigger_calc_damage
    ON survey.guo_huai_chi_huo_larva;

CREATE TRIGGER trigger_calc_damage
    BEFORE INSERT OR UPDATE
    ON survey.guo_huai_chi_huo_larva
    FOR EACH ROW
    EXECUTE FUNCTION survey.calculate_damage_level();

ALTER TABLE sites.sophora_sites
    ADD COLUMN IF NOT EXISTS "国槐尺蠖_2026年_幼虫发生情况" character varying;

COMMENT ON COLUMN sites.sophora_sites."国槐尺蠖_2026年_幼虫发生情况"
    IS '国槐尺蠖幼虫调查追踪器更新字段';

CREATE OR REPLACE VIEW views."2026_国槐尺蠖幼虫调查" AS
SELECT
    s.gid,
    s.geom,
    s."编号",
    s."乡镇",
    s."村",
    l."调查日期",
    l."总虫口数",
    l."危害程度",
    l."平均虫口数",
    s."国槐尺蠖_2026年_幼虫发生情况"
FROM sites.sophora_sites AS s
LEFT JOIN (
    SELECT
        c."编号",
        max(c."调查日期") AS "调查日期",
        sum(COALESCE(c."总虫口数", 0))::integer AS "总虫口数",
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
        END::character varying AS "危害程度",
        sum(COALESCE(c."平均虫口数", 0))::integer AS "平均虫口数"
    FROM survey.guo_huai_chi_huo_larva AS c
    GROUP BY c."编号"
) AS l ON s."编号" = l."编号";
