import { defineComponent } from "vue";
import { mount } from "@vue/test-utils";
import { describe, expect, it } from "vitest";

import WorkOrderView from "../WorkOrderView.vue";

const RecordTableStub = defineComponent({
  name: "RecordTable",
  template: '<div data-testid="record-table">记录表格</div>',
});

function mountWorkOrderView() {
  return mount(WorkOrderView, {
    global: {
      stubs: {
        RecordTable: RecordTableStub,
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
    expect(wrapper.text()).toContain("快捷操作");
    expect(wrapper.get('[data-testid="record-table"]').text()).toContain("记录表格");
  });
});
