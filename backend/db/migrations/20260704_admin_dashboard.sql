-- Migration: 20260704_admin_dashboard
-- Create app_admin schema and layer_metadata table for Dashboard admin backend

BEGIN;

CREATE SCHEMA IF NOT EXISTS app_admin;

CREATE TABLE IF NOT EXISTS app_admin.layer_metadata (
    id          BIGSERIAL PRIMARY KEY,
    layer_key   TEXT NOT NULL,
    layer_type  TEXT NOT NULL CHECK (layer_type IN ('view', 'reference')),
    display_name TEXT NULL,
    sort_order  INT NOT NULL DEFAULT 0,
    default_visible BOOLEAN NOT NULL DEFAULT FALSE,
    is_enabled  BOOLEAN NOT NULL DEFAULT TRUE,
    updated_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE UNIQUE INDEX IF NOT EXISTS idx_layer_metadata_type_key
    ON app_admin.layer_metadata (layer_type, layer_key);

CREATE OR REPLACE FUNCTION app_admin.seed_layer_metadata()
RETURNS void AS $$
DECLARE
    rec RECORD;
    existing_count INT;
BEGIN
    -- Seed views (map layers)
    FOR rec IN
        SELECT v.table_name
        FROM information_schema.views AS v
        JOIN information_schema.columns AS c
          ON c.table_schema = v.table_schema AND c.table_name = v.table_name
        WHERE v.table_schema = 'views'
        GROUP BY v.table_name
        HAVING BOOL_OR(c.column_name = 'geom')
        ORDER BY v.table_name
    LOOP
        SELECT COUNT(*) INTO existing_count
        FROM app_admin.layer_metadata
        WHERE layer_type = 'view' AND layer_key = rec.table_name;

        IF existing_count = 0 THEN
            INSERT INTO app_admin.layer_metadata (layer_key, layer_type, sort_order)
            VALUES (rec.table_name, 'view', 0);
        END IF;
    END LOOP;

    -- Seed reference layers, default_visible = TRUE for 通州区行政区边界
    FOR rec IN
        SELECT t.table_name,
               COALESCE(obj_description(
                   (quote_ident(t.table_schema) || '.' || quote_ident(t.table_name))::regclass,
                   'pg_class'
               ), t.table_name) AS label
        FROM information_schema.tables AS t
        JOIN information_schema.columns AS c
          ON c.table_schema = t.table_schema AND c.table_name = t.table_name
        WHERE t.table_schema = 'reference'
          AND t.table_type = 'BASE TABLE'
        GROUP BY t.table_schema, t.table_name
        HAVING BOOL_OR(c.column_name = 'geom')
        ORDER BY t.table_name
    LOOP
        SELECT COUNT(*) INTO existing_count
        FROM app_admin.layer_metadata
        WHERE layer_type = 'reference' AND layer_key = rec.table_name;

        IF existing_count = 0 THEN
            INSERT INTO app_admin.layer_metadata (
                layer_key, layer_type, display_name, sort_order, default_visible
            )
            VALUES (
                rec.table_name,
                'reference',
                rec.label,
                0,
                rec.table_name = '通州区行政区边界'
            );
        END IF;
    END LOOP;
END;
$$ LANGUAGE plpgsql;

SELECT app_admin.seed_layer_metadata();

DROP FUNCTION IF EXISTS app_admin.seed_layer_metadata();

COMMIT;
