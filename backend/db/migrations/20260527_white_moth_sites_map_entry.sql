CREATE SCHEMA IF NOT EXISTS sites;
CREATE SCHEMA IF NOT EXISTS views;

CREATE TABLE IF NOT EXISTS sites.white_moth_sites (
    "编号" character varying NOT NULL,
    geom geometry(Point, 4326),
    gid integer,
    "乡镇" character varying,
    "点位名称" character varying,
    CONSTRAINT white_moth_sites_pkey PRIMARY KEY ("编号")
);

CREATE SEQUENCE IF NOT EXISTS sites.white_moth_sites_gid_seq;

ALTER SEQUENCE sites.white_moth_sites_gid_seq
    OWNED BY sites.white_moth_sites.gid;

DO $$
DECLARE
    max_gid integer;
BEGIN
    SELECT COALESCE(MAX(gid), 0)
    INTO max_gid
    FROM sites.white_moth_sites;

    PERFORM setval(
        'sites.white_moth_sites_gid_seq',
        GREATEST(max_gid, 1),
        max_gid > 0
    );
END $$;

ALTER TABLE sites.white_moth_sites
    ALTER COLUMN gid SET DEFAULT nextval('sites.white_moth_sites_gid_seq'::regclass);

CREATE OR REPLACE VIEW views."美国白蛾点位" AS
SELECT
    s.gid,
    s.geom,
    BTRIM(s."编号") AS "编号",
    NULLIF(BTRIM(s."乡镇"), '') AS "乡镇",
    NULLIF(BTRIM(COALESCE(s."点位名称", '')), '') AS "点位名称"
FROM sites.white_moth_sites AS s
WHERE s.geom IS NOT NULL;

COMMENT ON VIEW views."美国白蛾点位"
    IS '美国白蛾基础点位地图视图，供调查员在地图端新增和查看点位';
