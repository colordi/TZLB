import { defineComponent } from "vue";
import { mount } from "@vue/test-utils";
import { describe, expect, it } from "vitest";

import { createEmptyRecord } from "../../components/workorder/fieldConfig.js";
import WorkOrderView from "../WorkOrderView.vue";

const RecordTableStub = defineComponent({
  name: "RecordTable",
  props: {
    records: {
      type: Array,
      default: () => [],
    },
  },
  emits: ["update:records"],
  template: '<div data-testid="record-table">记录表格 {{ records.length }}</div>',
});

const SurveyImportDialogStub = defineComponent({
  name: "SurveyImportDialog",
  props: {
    open: {
      type: Boolean,
      default: false,
    },
  },
  emits: ["close", "import"],
  template: '<div data-testid="survey-import-dialog" :data-open="open ? \'yes\' : \'no\'" />',
});

function mountWorkOrderView() {
  return mount(WorkOrderView, {
    global: {
      stubs: {
        RecordTable: RecordTableStub,
        SurveyImportDialog: SurveyImportDialogStub,
      },
    },
  });
}

describe("WorkOrderView", () => {
  it("移除页面介绍模块后仍保留侧栏和主表格", () => {
    const wrapper = mountWorkOrderView();

    expect(wrapper.find(".page-title-row").exists()).toBe(false);
    expect(wrapper.find(".workspace-intro").exists()).toBe(false);
    expect(wrapper.text()).not.toContain("工单录入");
    expect(wrapper.text()).not.toContain("支持表格批量粘贴");
    expect(wrapper.text()).not.toContain("现场记录");
    expect(wrapper.text()).toContain("录入概览");
    expect(wrapper.text()).toContain("任务配置");
    expect(wrapper.text()).toContain("生成工作单");
    expect(wrapper.get('[data-testid="record-table"]').text()).toContain("记录表格");
  });

  it("春尺蠖显示调查导入入口，切换害虫后隐藏", async () => {
    const wrapper = mountWorkOrderView();

    expect(wrapper.find('[data-testid="survey-import-button"]').exists()).toBe(true);

    await wrapper.get("#pest-type").setValue("国槐尺蠖");

    expect(wrapper.find('[data-testid="survey-import-button"]').exists()).toBe(false);
  });

  it("导入调查记录时会替换初始空白行，并在已有记录时追加", async () => {
    const wrapper = mountWorkOrderView();
    const recordTable = wrapper.getComponent(RecordTableStub);
    const surveyDialog = wrapper.getComponent(SurveyImportDialogStub);

    await wrapper.get('[data-testid="survey-import-button"]').trigger("click");
    expect(surveyDialog.props("open")).toBe(true);

    surveyDialog.vm.$emit("import", [
      {
        survey_date: "2026-04-01",
        town_or_street: "于家务乡",
        location_id: "YF0069",
        location_name: "神仙村",
        total_insect_count: 50,
        damage_level: "重",
        note: "",
        description: "描述1",
      },
    ]);
    await wrapper.vm.$nextTick();

    expect(recordTable.props("records")).toHaveLength(1);
    expect(recordTable.props("records")[0].location_id).toBe("YF0069");

    recordTable.vm.$emit("update:records", [
      {
        ...createEmptyRecord("春尺蠖"),
        survey_date: "2026-04-01",
        town_or_street: "西集镇",
        location_id: "XJ0001",
        location_name: "林场一区",
        description: "已有记录",
      },
    ]);
    await wrapper.vm.$nextTick();

    surveyDialog.vm.$emit("import", [
      {
        survey_date: "2026-04-02",
        town_or_street: "漷县镇",
        location_id: "HX0002",
        location_name: "林场二区",
        total_insect_count: 28,
        damage_level: "中",
        note: "需跟进",
        description: "描述2",
      },
    ]);
    await wrapper.vm.$nextTick();

    expect(recordTable.props("records")).toHaveLength(2);
    expect(recordTable.props("records")[0].location_id).toBe("XJ0001");
    expect(recordTable.props("records")[1].location_id).toBe("HX0002");
  });
});
