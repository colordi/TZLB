BEGIN;

CREATE OR REPLACE FUNCTION pg_temp.rename_column_if_present(
    schema_name text,
    relation_name text,
    old_column_name text,
    new_column_name text
) RETURNS void
LANGUAGE plpgsql
AS $$
DECLARE
    relation_oid oid;
    relation_kind "char";
    old_exists boolean;
    new_exists boolean;
    alter_command text;
BEGIN
    SELECT c.oid, c.relkind
      INTO relation_oid, relation_kind
    FROM pg_class AS c
    JOIN pg_namespace AS n
      ON n.oid = c.relnamespace
    WHERE n.nspname = schema_name
      AND c.relname = relation_name
      AND c.relkind IN ('r', 'p', 'v', 'm', 'f');

    IF relation_oid IS NULL THEN
        RETURN;
    END IF;

    SELECT EXISTS (
        SELECT 1
        FROM pg_attribute
        WHERE attrelid = relation_oid
          AND attname = old_column_name
          AND attnum > 0
          AND NOT attisdropped
    ) INTO old_exists;

    SELECT EXISTS (
        SELECT 1
        FROM pg_attribute
        WHERE attrelid = relation_oid
          AND attname = new_column_name
          AND attnum > 0
          AND NOT attisdropped
    ) INTO new_exists;

    IF old_exists AND new_exists THEN
        RAISE EXCEPTION '%.% 同时存在列 % 和 %，请先人工核查',
            schema_name, relation_name, old_column_name, new_column_name;
    END IF;

    IF NOT old_exists OR new_exists THEN
        RETURN;
    END IF;

    alter_command := CASE relation_kind
        WHEN 'v' THEN 'ALTER VIEW'
        WHEN 'm' THEN 'ALTER MATERIALIZED VIEW'
        WHEN 'f' THEN 'ALTER FOREIGN TABLE'
        ELSE 'ALTER TABLE'
    END;

    EXECUTE format(
        '%s %I.%I RENAME COLUMN %I TO %I',
        alter_command,
        schema_name,
        relation_name,
        old_column_name,
        new_column_name
    );
END;
$$;

CREATE OR REPLACE FUNCTION pg_temp.rebuild_view_identifier(
    schema_name text,
    view_name text,
    old_identifier text,
    new_identifier text
) RETURNS void
LANGUAGE plpgsql
AS $$
DECLARE
    view_oid oid;
    view_sql text;
    rewritten_sql text;
BEGIN
    SELECT c.oid
      INTO view_oid
    FROM pg_class AS c
    JOIN pg_namespace AS n
      ON n.oid = c.relnamespace
    WHERE n.nspname = schema_name
      AND c.relname = view_name
      AND c.relkind = 'v';

    IF view_oid IS NULL THEN
        RETURN;
    END IF;

    view_sql := pg_get_viewdef(view_oid, true);
    rewritten_sql := replace(
        view_sql,
        format('%I', old_identifier),
        format('%I', new_identifier)
    );

    IF rewritten_sql = view_sql THEN
        RETURN;
    END IF;

    EXECUTE format(
        'CREATE OR REPLACE VIEW %I.%I AS %s',
        schema_name,
        view_name,
        rewritten_sql
    );
END;
$$;

CREATE OR REPLACE FUNCTION pg_temp.comment_column_if_present(
    schema_name text,
    relation_name text,
    column_name text,
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
      AND c.relname = relation_name
      AND c.relkind IN ('r', 'p', 'v', 'm', 'f');

    IF relation_oid IS NULL THEN
        RETURN;
    END IF;

    IF NOT EXISTS (
        SELECT 1
        FROM pg_attribute
        WHERE attrelid = relation_oid
          AND attname = column_name
          AND attnum > 0
          AND NOT attisdropped
    ) THEN
        RETURN;
    END IF;

    EXECUTE format(
        'COMMENT ON COLUMN %I.%I.%I IS %L',
        schema_name,
        relation_name,
        column_name,
        comment_text
    );
END;
$$;

SELECT pg_temp.rename_column_if_present('ledger', '2026年其他害虫问题点位事件流水表', '乡镇', '属地');
SELECT pg_temp.rename_column_if_present('ledger', '2026年国槐尺蠖问题点位事件流水表', '乡镇', '属地');
SELECT pg_temp.rename_column_if_present('ledger', '2026年春尺蠖问题点位事件流水表', '乡镇', '属地');
SELECT pg_temp.rename_column_if_present('ledger', '2026年美国白蛾第一代问题点位事件流水表', '乡镇', '属地');
SELECT pg_temp.rename_column_if_present('reference', 'tongzhou_communities', '乡镇', '属地');
SELECT pg_temp.rename_column_if_present('reference', 'tongzhou_sophora_layer', '乡镇', '属地');
SELECT pg_temp.rename_column_if_present('sites', 'other_pest_sites', '乡镇', '属地');
SELECT pg_temp.rename_column_if_present('sites', 'poplar_sites', '乡镇', '属地');
SELECT pg_temp.rename_column_if_present('sites', 'sophora_sites', '乡镇', '属地');
SELECT pg_temp.rename_column_if_present('sites', 'white_moth_sites', '乡镇', '属地');
SELECT pg_temp.rename_column_if_present('survey', 'mei_guo_bai_e_first_generation_inspection', '乡镇', '属地');

SELECT pg_temp.rename_column_if_present('ledger', '2026年其他害虫问题点位台账', '乡镇', '属地');
SELECT pg_temp.rename_column_if_present('ledger', '2026年国槐尺蠖问题点位台账', '乡镇', '属地');
SELECT pg_temp.rename_column_if_present('ledger', '2026年春尺蠖问题点位台账', '乡镇', '属地');
SELECT pg_temp.rename_column_if_present('ledger', '2026年美国白蛾第一代问题点位台账', '乡镇', '属地');
SELECT pg_temp.rename_column_if_present('views', '2026_其他害虫调查', '乡镇', '属地');
SELECT pg_temp.rename_column_if_present('views', '2026_国槐尺蠖幼虫调查', '乡镇', '属地');
SELECT pg_temp.rename_column_if_present('views', '2026_春尺蠖幼虫调查', '乡镇', '属地');
SELECT pg_temp.rename_column_if_present('views', '2026_春尺蠖成虫调查', '乡镇', '属地');
SELECT pg_temp.rename_column_if_present('views', '2026_美国白蛾第 1 代调查', '乡镇', '属地');
SELECT pg_temp.rename_column_if_present('views', '国槐尺蠖幼虫历年发生情况', '乡镇', '属地');
SELECT pg_temp.rename_column_if_present('views', '美国白蛾点位', '乡镇', '属地');

SELECT pg_temp.rebuild_view_identifier('ledger', '2026年其他害虫问题点位台账', '乡镇', '属地');
SELECT pg_temp.rebuild_view_identifier('ledger', '2026年国槐尺蠖问题点位台账', '乡镇', '属地');
SELECT pg_temp.rebuild_view_identifier('ledger', '2026年春尺蠖问题点位台账', '乡镇', '属地');
SELECT pg_temp.rebuild_view_identifier('ledger', '2026年美国白蛾第一代问题点位台账', '乡镇', '属地');
SELECT pg_temp.rebuild_view_identifier('views', '2026_其他害虫调查', '乡镇', '属地');
SELECT pg_temp.rebuild_view_identifier('views', '2026_国槐尺蠖幼虫调查', '乡镇', '属地');
SELECT pg_temp.rebuild_view_identifier('views', '2026_春尺蠖幼虫调查', '乡镇', '属地');
SELECT pg_temp.rebuild_view_identifier('views', '2026_春尺蠖成虫调查', '乡镇', '属地');
SELECT pg_temp.rebuild_view_identifier('views', '2026_美国白蛾第 1 代调查', '乡镇', '属地');
SELECT pg_temp.rebuild_view_identifier('views', '国槐尺蠖幼虫历年发生情况', '乡镇', '属地');
SELECT pg_temp.rebuild_view_identifier('views', '美国白蛾点位', '乡镇', '属地');

SELECT pg_temp.comment_column_if_present(
    'survey',
    'mei_guo_bai_e_first_generation_inspection',
    '属地',
    '巡查时点位所属属地快照'
);
SELECT pg_temp.comment_column_if_present(
    'sites',
    'white_moth_sites',
    '属地',
    '美国白蛾点位所属属地'
);

COMMIT;
