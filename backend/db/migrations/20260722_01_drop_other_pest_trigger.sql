-- 废除其他害虫调查表的事件流水同步触发器。
-- 事件流水改为用户手工填写 ledger sheet 导入，事件类型由后端在导入时
-- 基于历史事件做对比纠正（调查下派 -> 复查异常），不再由数据库触发器生成。

BEGIN;

DROP TRIGGER IF EXISTS trg_sync_other_pest_event_on_inspection ON survey."其他害虫调查表";
DROP FUNCTION IF EXISTS survey.sync_other_pest_event_from_inspection();

COMMIT;
