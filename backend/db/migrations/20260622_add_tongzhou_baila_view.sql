BEGIN;

CREATE OR REPLACE VIEW views."通州白蜡图层" AS
SELECT *
FROM reference."通州白蜡图层"
WHERE geom IS NOT NULL;

COMMENT ON VIEW views."通州白蜡图层"
    IS '通州白蜡图层地图视图，直接展示 reference.通州白蜡图层 原始字段';

COMMIT;
