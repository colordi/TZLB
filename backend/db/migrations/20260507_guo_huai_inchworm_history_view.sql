CREATE SCHEMA IF NOT EXISTS views;

CREATE OR REPLACE VIEW views."国槐尺蠖幼虫历年发生情况" AS
SELECT
    s.gid,
    s.geom,
    s."编号",
    s."乡镇",
    s."村",
    '国槐尺蠖'::text AS "害虫类型",
    '幼虫'::text AS "虫态",
    h."年份",
    h."发生情况",
    BTRIM(h."发生情况")::character varying AS "危害程度",
    h."来源字段"
FROM sites.sophora_sites AS s
CROSS JOIN LATERAL (
    VALUES
        (
            '2024'::text,
            s."国槐尺蠖_2024年_幼虫发生情况"::text,
            '国槐尺蠖_2024年_幼虫发生情况'::text
        ),
        (
            '2025'::text,
            s."国槐尺蠖_2025年_幼虫发生情况"::text,
            '国槐尺蠖_2025年_幼虫发生情况'::text
        ),
        (
            '2026'::text,
            s."国槐尺蠖_2026年_幼虫发生情况"::text,
            '国槐尺蠖_2026年_幼虫发生情况'::text
        )
) AS h("年份", "发生情况", "来源字段")
WHERE s.geom IS NOT NULL
  AND NULLIF(BTRIM(COALESCE(h."发生情况", '')), '') IS NOT NULL;
