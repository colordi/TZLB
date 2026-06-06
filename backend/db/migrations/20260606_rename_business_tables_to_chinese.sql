BEGIN;

CREATE OR REPLACE FUNCTION pg_temp.rename_business_table_if_present(
    schema_name text,
    old_table_name text,
    new_table_name text
) RETURNS void
LANGUAGE plpgsql
AS $$
DECLARE
    old_relation_oid oid;
    new_relation_oid oid;
BEGIN
    SELECT c.oid
      INTO old_relation_oid
    FROM pg_class AS c
    JOIN pg_namespace AS n
      ON n.oid = c.relnamespace
    WHERE n.nspname = schema_name
      AND c.relname = old_table_name
      AND c.relkind IN ('r', 'p');

    SELECT c.oid
      INTO new_relation_oid
    FROM pg_class AS c
    JOIN pg_namespace AS n
      ON n.oid = c.relnamespace
    WHERE n.nspname = schema_name
      AND c.relname = new_table_name;

    IF old_relation_oid IS NOT NULL AND new_relation_oid IS NOT NULL THEN
        RAISE EXCEPTION '%.% 和 %.% 同时存在，请先人工核查',
            schema_name, old_table_name, schema_name, new_table_name;
    END IF;

    IF old_relation_oid IS NULL THEN
        RETURN;
    END IF;

    EXECUTE format(
        'ALTER TABLE %I.%I RENAME TO %I',
        schema_name,
        old_table_name,
        new_table_name
    );
END;
$$;

CREATE OR REPLACE FUNCTION pg_temp.comment_business_table_if_present(
    schema_name text,
    table_name text,
    comment_text text
) RETURNS void
LANGUAGE plpgsql
AS $$
DECLARE
    relation_oid oid;
BEGIN
    SELECT c.oid
      INTO relation_oid
    FROM pg_class AS c
    JOIN pg_namespace AS n
      ON n.oid = c.relnamespace
    WHERE n.nspname = schema_name
      AND c.relname = table_name
      AND c.relkind IN ('r', 'p');

    IF relation_oid IS NULL THEN
        RETURN;
    END IF;

    EXECUTE format(
        'COMMENT ON TABLE %I.%I IS %L',
        schema_name,
        table_name,
        comment_text
    );
END;
$$;

SELECT pg_temp.rename_business_table_if_present(
    'survey',
    'chun_chi_huo_adult',
    '春尺蠖成虫调查表'
);
SELECT pg_temp.rename_business_table_if_present(
    'survey',
    'chun_chi_huo_larva',
    '春尺蠖幼虫调查表'
);
SELECT pg_temp.rename_business_table_if_present(
    'survey',
    'chun_chi_huo_trap',
    '春尺蠖围环调查表'
);
SELECT pg_temp.rename_business_table_if_present(
    'survey',
    'guo_huai_chi_huo_larva',
    '国槐尺蠖幼虫调查表'
);
SELECT pg_temp.rename_business_table_if_present(
    'survey',
    'mei_guo_bai_e_first_generation_inspection',
    '美国白蛾第一代调查表'
);
SELECT pg_temp.rename_business_table_if_present(
    'survey',
    '美国白蛾第一代巡查表',
    '美国白蛾第一代调查表'
);
SELECT pg_temp.rename_business_table_if_present(
    'survey',
    'other_pest_inspection',
    '其他害虫调查表'
);
SELECT pg_temp.rename_business_table_if_present(
    'reference',
    'admin_boundary',
    '通州区行政区边界'
);
SELECT pg_temp.rename_business_table_if_present(
    'reference',
    '行政区边界表',
    '通州区行政区边界'
);
SELECT pg_temp.rename_business_table_if_present(
    'reference',
    'tongzhou_communities',
    '通州区小区边界'
);
SELECT pg_temp.rename_business_table_if_present(
    'reference',
    '通州社区点位基础表',
    '通州区小区边界'
);
SELECT pg_temp.rename_business_table_if_present(
    'reference',
    'tongzhou_sophora_layer',
    '通州国槐图层'
);
SELECT pg_temp.rename_business_table_if_present(
    'reference',
    '通州国槐图层表',
    '通州国槐图层'
);
SELECT pg_temp.rename_business_table_if_present(
    'reference',
    'tongzhou_villages',
    '通州区村庄边界'
);
SELECT pg_temp.rename_business_table_if_present(
    'reference',
    '通州村庄边界表',
    '通州区村庄边界'
);
SELECT pg_temp.rename_business_table_if_present(
    'sites',
    'monitoring_sites',
    '监测点位基础表'
);
SELECT pg_temp.rename_business_table_if_present(
    'sites',
    'other_pest_sites',
    '其他害虫点位基础表'
);
SELECT pg_temp.rename_business_table_if_present(
    'sites',
    'poplar_sites',
    '杨树点位基础表'
);
SELECT pg_temp.rename_business_table_if_present(
    'sites',
    'sophora_sites',
    '国槐点位基础表'
);
SELECT pg_temp.rename_business_table_if_present(
    'sites',
    'white_moth_sites',
    '美国白蛾点位基础表'
);

SELECT pg_temp.comment_business_table_if_present('survey', '春尺蠖成虫调查表', '春尺蠖成虫调查表');
SELECT pg_temp.comment_business_table_if_present('survey', '春尺蠖幼虫调查表', '春尺蠖幼虫调查表');
SELECT pg_temp.comment_business_table_if_present('survey', '春尺蠖围环调查表', '春尺蠖围环调查表');
SELECT pg_temp.comment_business_table_if_present('survey', '国槐尺蠖幼虫调查表', '国槐尺蠖幼虫调查表');
SELECT pg_temp.comment_business_table_if_present('survey', '美国白蛾第一代调查表', '美国白蛾第一代调查表');
SELECT pg_temp.comment_business_table_if_present('survey', '其他害虫调查表', '其他害虫调查表');
SELECT pg_temp.comment_business_table_if_present('reference', '通州区行政区边界', '通州区行政区边界');
SELECT pg_temp.comment_business_table_if_present('reference', '通州区小区边界', '通州区小区边界');
SELECT pg_temp.comment_business_table_if_present('reference', '通州国槐图层', '通州国槐图层');
SELECT pg_temp.comment_business_table_if_present('reference', '通州区村庄边界', '通州区村庄边界');
SELECT pg_temp.comment_business_table_if_present('sites', '监测点位基础表', '监测点位基础表');
SELECT pg_temp.comment_business_table_if_present('sites', '其他害虫点位基础表', '其他害虫点位基础表');
SELECT pg_temp.comment_business_table_if_present('sites', '杨树点位基础表', '杨树点位基础表');
SELECT pg_temp.comment_business_table_if_present('sites', '国槐点位基础表', '国槐点位基础表');
SELECT pg_temp.comment_business_table_if_present('sites', '美国白蛾点位基础表', '美国白蛾点位基础表');

COMMIT;
