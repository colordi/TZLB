-- 阶段2迁移：survey/ledger/sites/reference 表结构变更
-- 1. survey 各调查表加"年份"列，美国白蛾/国槐尺蠖加"世代"列，改主键
-- 2. ledger 事件流水表加"年份"/"世代"列，重命名（去年度/世代后缀）
-- 3. sites."杨树点位基础表" 加"当前点位状态"字段，DROP 所有年度宽字段
-- 4. sites."国槐点位基础表" DROP 年度宽字段
-- 5. reference."通州区小区边界" DROP 年度宽字段
-- 前置条件：已执行 pg_dump 备份

BEGIN;

-- 先 DROP 所有依赖视图（含 views 和 ledger 台账视图），避免 DROP COLUMN 时依赖冲突
DROP VIEW IF EXISTS views."2026_美国白蛾第 1 代调查";
DROP VIEW IF EXISTS views."2026_国槐尺蠖幼虫调查";
DROP VIEW IF EXISTS views."2026_春尺蠖幼虫调查";
DROP VIEW IF EXISTS views."2026_春尺蠖成虫调查";
DROP VIEW IF EXISTS views."2026_其他害虫调查";
DROP VIEW IF EXISTS views."国槐尺蠖幼虫历年发生情况";
DROP VIEW IF EXISTS ledger."2026年美国白蛾第一代问题点位台账";
DROP VIEW IF EXISTS ledger."2026年国槐尺蠖问题点位台账";
DROP VIEW IF EXISTS ledger."2026年春尺蠖问题点位台账";
DROP VIEW IF EXISTS ledger."2026年其他害虫问题点位台账";

-- ============================================================
-- 1. survey 表：加年份/世代列，改主键
-- ============================================================

-- 1.1 美国白蛾调查表（原名"美国白蛾第一代调查表"）
ALTER TABLE survey."美国白蛾第一代调查表" ADD COLUMN IF NOT EXISTS "年份" integer NOT NULL DEFAULT 2026;
ALTER TABLE survey."美国白蛾第一代调查表" ADD COLUMN IF NOT EXISTS "世代" text NOT NULL DEFAULT '第一代';
ALTER TABLE survey."美国白蛾第一代调查表" DROP CONSTRAINT IF EXISTS mgb1_unique_location_date;
ALTER TABLE survey."美国白蛾第一代调查表" DROP CONSTRAINT IF EXISTS mei_guo_bai_e_first_generation_inspection_pkey;
ALTER TABLE survey."美国白蛾第一代调查表" ADD CONSTRAINT mgb_inspection_generation_check CHECK ("世代" IN ('第一代','第二代','第三代'));
ALTER TABLE survey."美国白蛾第一代调查表" ADD PRIMARY KEY ("编号", "调查日期", "年份", "世代");
ALTER TABLE survey."美国白蛾第一代调查表" RENAME TO "美国白蛾调查表";

-- 1.2 国槐尺蠖幼虫调查表
ALTER TABLE survey."国槐尺蠖幼虫调查表" ADD COLUMN IF NOT EXISTS "年份" integer NOT NULL DEFAULT 2026;
ALTER TABLE survey."国槐尺蠖幼虫调查表" ADD COLUMN IF NOT EXISTS "世代" text NOT NULL DEFAULT '第一代';
UPDATE survey."国槐尺蠖幼虫调查表" SET "年份" = EXTRACT(YEAR FROM "调查日期")::integer;
ALTER TABLE survey."国槐尺蠖幼虫调查表" DROP CONSTRAINT IF EXISTS guo_huai_chi_huo_larva_pkey;
ALTER TABLE survey."国槐尺蠖幼虫调查表" ADD CONSTRAINT guo_huai_chi_huo_larva_generation_check CHECK ("世代" IN ('第一代','第二代','第三代'));
ALTER TABLE survey."国槐尺蠖幼虫调查表" ADD PRIMARY KEY ("编号", "调查日期", "年份", "世代");

-- 1.3 春尺蠖幼虫调查表
ALTER TABLE survey."春尺蠖幼虫调查表" ADD COLUMN IF NOT EXISTS "年份" integer NOT NULL DEFAULT 2026;
UPDATE survey."春尺蠖幼虫调查表" SET "年份" = EXTRACT(YEAR FROM "调查日期")::integer;
ALTER TABLE survey."春尺蠖幼虫调查表" DROP CONSTRAINT IF EXISTS chun_chi_huo_larva_pkey;
ALTER TABLE survey."春尺蠖幼虫调查表" ADD PRIMARY KEY ("编号", "调查日期", "年份");

-- 1.4 春尺蠖成虫调查表
ALTER TABLE survey."春尺蠖成虫调查表" ADD COLUMN IF NOT EXISTS "年份" integer NOT NULL DEFAULT 2026;
UPDATE survey."春尺蠖成虫调查表" SET "年份" = EXTRACT(YEAR FROM "调查日期")::integer WHERE "调查日期" IS NOT NULL;
ALTER TABLE survey."春尺蠖成虫调查表" DROP CONSTRAINT IF EXISTS chun_chi_huo_adult_unique;
ALTER TABLE survey."春尺蠖成虫调查表" ADD CONSTRAINT chun_chi_huo_adult_unique UNIQUE ("编号", "调查日期", "年份");

-- 1.5 春尺蠖围环调查表
ALTER TABLE survey."春尺蠖围环调查表" ADD COLUMN IF NOT EXISTS "年份" integer NOT NULL DEFAULT 2026;
UPDATE survey."春尺蠖围环调查表" SET "年份" = EXTRACT(YEAR FROM "围环日期")::integer WHERE "围环日期" IS NOT NULL;
ALTER TABLE survey."春尺蠖围环调查表" DROP CONSTRAINT IF EXISTS chun_chi_huo_trap_pkey;
ALTER TABLE survey."春尺蠖围环调查表" ADD PRIMARY KEY ("编号", "年份");

-- 1.6 其他害虫调查表
ALTER TABLE survey."其他害虫调查表" ADD COLUMN IF NOT EXISTS "年份" integer NOT NULL DEFAULT 2026;
UPDATE survey."其他害虫调查表" SET "年份" = EXTRACT(YEAR FROM "调查日期")::integer;
ALTER TABLE survey."其他害虫调查表" DROP CONSTRAINT IF EXISTS other_pest_inspection_pkey;
ALTER TABLE survey."其他害虫调查表" ADD PRIMARY KEY ("编号", "虫害类型", "调查日期", "年份");

-- ============================================================
-- 2. ledger 事件流水表：加年份/世代列，重命名
-- ============================================================

-- 2.1 美国白蛾事件流水表
ALTER TABLE ledger."2026年美国白蛾第一代问题点位事件流水表" ADD COLUMN IF NOT EXISTS "年份" integer NOT NULL DEFAULT 2026;
ALTER TABLE ledger."2026年美国白蛾第一代问题点位事件流水表" ADD COLUMN IF NOT EXISTS "世代" text NOT NULL DEFAULT '第一代';
ALTER TABLE ledger."2026年美国白蛾第一代问题点位事件流水表" ADD CONSTRAINT mgb_ledger_generation_check CHECK ("世代" IN ('第一代','第二代','第三代'));
ALTER TABLE ledger."2026年美国白蛾第一代问题点位事件流水表" RENAME TO "美国白蛾问题点位事件流水表";

-- 2.2 国槐尺蠖事件流水表
ALTER TABLE ledger."2026年国槐尺蠖问题点位事件流水表" ADD COLUMN IF NOT EXISTS "年份" integer NOT NULL DEFAULT 2026;
ALTER TABLE ledger."2026年国槐尺蠖问题点位事件流水表" ADD COLUMN IF NOT EXISTS "世代" text NOT NULL DEFAULT '第一代';
ALTER TABLE ledger."2026年国槐尺蠖问题点位事件流水表" ADD CONSTRAINT guo_huai_ledger_generation_check CHECK ("世代" IN ('第一代','第二代','第三代'));
ALTER TABLE ledger."2026年国槐尺蠖问题点位事件流水表" RENAME TO "国槐尺蠖问题点位事件流水表";

-- 2.3 春尺蠖事件流水表
ALTER TABLE ledger."2026年春尺蠖问题点位事件流水表" ADD COLUMN IF NOT EXISTS "年份" integer NOT NULL DEFAULT 2026;
ALTER TABLE ledger."2026年春尺蠖问题点位事件流水表" RENAME TO "春尺蠖问题点位事件流水表";

-- 2.4 其他害虫事件流水表
ALTER TABLE ledger."2026年其他害虫问题点位事件流水表" ADD COLUMN IF NOT EXISTS "年份" integer NOT NULL DEFAULT 2026;
ALTER TABLE ledger."2026年其他害虫问题点位事件流水表" RENAME TO "其他害虫问题点位事件流水表";

-- ============================================================
-- 3. sites."杨树点位基础表"：加"当前点位状态"，DROP 年度宽字段
-- ============================================================

ALTER TABLE sites."杨树点位基础表" ADD COLUMN IF NOT EXISTS "当前点位状态" character varying NOT NULL DEFAULT '不可调查';
ALTER TABLE sites."杨树点位基础表" ADD CONSTRAINT poplar_sites_status_check CHECK ("当前点位状态" IN ('可调查','不可调查','伐除'));

-- 数据迁移：从旧宽字段映射到"当前点位状态"（伐优先）
UPDATE sites."杨树点位基础表" SET "当前点位状态" = '伐除'
WHERE "春尺蠖_2026年成虫发生情况" = '伐';
UPDATE sites."杨树点位基础表" SET "当前点位状态" = '可调查'
WHERE "春尺蠖_2026年_围环发生情况" = '可调查'
  AND "当前点位状态" = '不可调查';

-- DROP 所有年度宽字段
ALTER TABLE sites."杨树点位基础表" DROP COLUMN IF EXISTS "食叶害虫_2023年_发生情况";
ALTER TABLE sites."杨树点位基础表" DROP COLUMN IF EXISTS "食叶害虫_2024年_发生情况";
ALTER TABLE sites."杨树点位基础表" DROP COLUMN IF EXISTS "春尺蠖_2019年_幼虫发生情况";
ALTER TABLE sites."杨树点位基础表" DROP COLUMN IF EXISTS "春尺蠖_2024年_越冬基数发生情况";
ALTER TABLE sites."杨树点位基础表" DROP COLUMN IF EXISTS "春尺蠖_2024年_幼虫发生情况";
ALTER TABLE sites."杨树点位基础表" DROP COLUMN IF EXISTS "春尺蠖_2025年_围环发生情况";
ALTER TABLE sites."杨树点位基础表" DROP COLUMN IF EXISTS "春尺蠖_2025年_越冬基数发生情况";
ALTER TABLE sites."杨树点位基础表" DROP COLUMN IF EXISTS "春尺蠖_2025年_成虫发生情况";
ALTER TABLE sites."杨树点位基础表" DROP COLUMN IF EXISTS "春尺蠖_2025年_幼虫发生情况";
ALTER TABLE sites."杨树点位基础表" DROP COLUMN IF EXISTS "春尺蠖_2026年_围环发生情况";
ALTER TABLE sites."杨树点位基础表" DROP COLUMN IF EXISTS "春尺蠖_2026年成虫发生情况";

-- ============================================================
-- 4. sites."国槐点位基础表"：DROP 年度宽字段
-- ============================================================

ALTER TABLE sites."国槐点位基础表" DROP COLUMN IF EXISTS "国槐尺蠖_2024年_幼虫发生情况";
ALTER TABLE sites."国槐点位基础表" DROP COLUMN IF EXISTS "国槐尺蠖_2025年_幼虫发生情况";
ALTER TABLE sites."国槐点位基础表" DROP COLUMN IF EXISTS "国槐尺蠖_2026年_幼虫发生情况";

-- ============================================================
-- 5. reference."通州区小区边界"：DROP 年度宽字段
-- ============================================================

ALTER TABLE reference."通州区小区边界" DROP COLUMN IF EXISTS "25年1代受害株";
ALTER TABLE reference."通州区小区边界" DROP COLUMN IF EXISTS "25年2代受害株";
ALTER TABLE reference."通州区小区边界" DROP COLUMN IF EXISTS "25年3代受害株";
ALTER TABLE reference."通州区小区边界" DROP COLUMN IF EXISTS "25年景观害虫发生";

COMMIT;
