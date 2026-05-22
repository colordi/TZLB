CREATE SCHEMA IF NOT EXISTS survey;

CREATE TABLE IF NOT EXISTS survey.mei_guo_bai_e_first_generation_inspection (
    "编号" character varying NOT NULL,
    "调查日期" date NOT NULL,
    "区域" character varying NOT NULL DEFAULT '乡镇',
    "乡镇" character varying NOT NULL,
    "点位名称" character varying NOT NULL,
    "发生位置" character varying NOT NULL DEFAULT '',
    "绿地性质" character varying NOT NULL DEFAULT '',
    "危害寄主" character varying NOT NULL DEFAULT '',
    "受害株数" integer NOT NULL DEFAULT 0,
    "网幕数量" integer NOT NULL DEFAULT 0,
    "是否剪网" character varying NOT NULL DEFAULT '否',
    "剪网彻底" character varying NOT NULL DEFAULT '不涉及',
    "详细描述" text NOT NULL DEFAULT '',
    "备注" text NOT NULL DEFAULT '',
    CONSTRAINT mgb1_inspection_pkey PRIMARY KEY ("编号", "调查日期"),
    CONSTRAINT mgb1_region_check
        CHECK ("区域" IN ('城区', '乡镇')),
    CONSTRAINT mgb1_damaged_plant_count_check
        CHECK ("受害株数" >= 0),
    CONSTRAINT mgb1_web_nest_count_check
        CHECK ("网幕数量" >= 0),
    CONSTRAINT mgb1_pruning_status_check
        CHECK ("是否剪网" IN ('是', '否')),
    CONSTRAINT mgb1_pruning_complete_check
        CHECK ("剪网彻底" IN ('是', '否', '不涉及')),
    CONSTRAINT mgb1_pruning_consistency_check
        CHECK (
            ("是否剪网" = '否' AND "剪网彻底" = '不涉及')
            OR ("是否剪网" = '是' AND "剪网彻底" IN ('是', '否'))
        )
);

COMMENT ON TABLE survey.mei_guo_bai_e_first_generation_inspection
    IS '美国白蛾第一代巡查表';

COMMENT ON COLUMN survey.mei_guo_bai_e_first_generation_inspection."区域"
    IS '取值：城区、乡镇';

COMMENT ON COLUMN survey.mei_guo_bai_e_first_generation_inspection."乡镇"
    IS '巡查时点位所属乡镇或街道快照';

COMMENT ON COLUMN survey.mei_guo_bai_e_first_generation_inspection."点位名称"
    IS '巡查时点位名称快照';

COMMENT ON COLUMN survey.mei_guo_bai_e_first_generation_inspection."发生位置"
    IS '点位内美国白蛾发生的具体位置';

COMMENT ON COLUMN survey.mei_guo_bai_e_first_generation_inspection."绿地性质"
    IS '如平原造林、道路绿化、公园绿地、小区绿地等';

COMMENT ON COLUMN survey.mei_guo_bai_e_first_generation_inspection."是否剪网"
    IS '取值：是、否';

COMMENT ON COLUMN survey.mei_guo_bai_e_first_generation_inspection."剪网彻底"
    IS '取值：是、否、不涉及；未剪网时应为不涉及';
