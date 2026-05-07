WITH ranked_sites AS (
    SELECT
        gid,
        ROW_NUMBER() OVER (
            PARTITION BY BTRIM("编号")
            ORDER BY
                CASE WHEN geom IS NULL THEN 1 ELSE 0 END,
                CASE WHEN NULLIF(BTRIM(COALESCE("村", '')), '') IS NULL THEN 1 ELSE 0 END,
                gid
        ) AS keep_rank
    FROM sites.sophora_sites
)
DELETE FROM sites.sophora_sites AS s
USING ranked_sites AS r
WHERE s.gid = r.gid
  AND (
      s.geom IS NULL
      OR r.keep_rank > 1
  );
