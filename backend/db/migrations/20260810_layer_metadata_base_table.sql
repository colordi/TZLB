-- 任务视图绑定基础点位表与源定义，供地图通用「添加点位」使用。
-- 应用启动时 ensure_layer_metadata_storage 也会 ADD COLUMN IF NOT EXISTS。

ALTER TABLE app_admin.layer_metadata
  ADD COLUMN IF NOT EXISTS base_table TEXT NULL;

ALTER TABLE app_admin.layer_metadata
  ADD COLUMN IF NOT EXISTS source_definition JSONB NULL;
