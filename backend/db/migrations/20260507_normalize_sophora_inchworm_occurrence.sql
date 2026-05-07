UPDATE sites.sophora_sites
SET
    "国槐尺蠖_2024年_幼虫发生情况" = CASE
        WHEN BTRIM(COALESCE("国槐尺蠖_2024年_幼虫发生情况", '')) = '无需防治'
            THEN '白'
        ELSE "国槐尺蠖_2024年_幼虫发生情况"
    END,
    "国槐尺蠖_2025年_幼虫发生情况" = CASE
        WHEN BTRIM(COALESCE("国槐尺蠖_2025年_幼虫发生情况", '')) = '无需防治'
            THEN '白'
        ELSE "国槐尺蠖_2025年_幼虫发生情况"
    END,
    "国槐尺蠖_2026年_幼虫发生情况" = CASE
        WHEN BTRIM(COALESCE("国槐尺蠖_2026年_幼虫发生情况", '')) = '无需防治'
            THEN '白'
        ELSE "国槐尺蠖_2026年_幼虫发生情况"
    END
WHERE BTRIM(COALESCE("国槐尺蠖_2024年_幼虫发生情况", '')) = '无需防治'
   OR BTRIM(COALESCE("国槐尺蠖_2025年_幼虫发生情况", '')) = '无需防治'
   OR BTRIM(COALESCE("国槐尺蠖_2026年_幼虫发生情况", '')) = '无需防治';
