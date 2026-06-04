import { mount } from "@vue/test-utils";
import { afterEach, describe, expect, it, vi } from "vitest";

import DesignWorkOrderView from "../design/DesignWorkOrderView.vue";

function mountWorkOrder() {
  return mount(DesignWorkOrderView);
}

describe("DesignWorkOrderView", () => {
  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("使用静态记录完成本地搜索和状态筛选", async () => {
    const wrapper = mountWorkOrder();

    expect(wrapper.findAll(".design-workorder-table tbody tr")).toHaveLength(18);

    await wrapper.get('[data-testid="design-workorder-search"]').setValue("玉渊潭");
    expect(wrapper.findAll(".design-workorder-table tbody tr")).toHaveLength(1);
    expect(wrapper.text()).toContain("玉渊潭公园");

    await wrapper.get('[data-testid="design-workorder-search"]').setValue("");
    await wrapper.get('[data-testid="design-workorder-status-generated"]').trigger("click");

    expect(wrapper.findAll(".design-workorder-table tbody tr")).toHaveLength(5);
    expect(wrapper.get('[data-testid="design-workorder-status-generated"]').classes()).toContain(
      "is-active",
    );
  });

  it("选择状态只保存在页面本地并显示选择摘要", async () => {
    const wrapper = mountWorkOrder();
    const firstCheckbox = wrapper.find(".design-workorder-table tbody input[type='checkbox']");

    await firstCheckbox.setValue(true);

    expect(wrapper.get('[data-testid="design-workorder-batch-bar"]').text()).toContain(
      "已选 1 条记录",
    );
    expect(wrapper.text()).toContain("已选 1 条");

    await wrapper
      .get('[data-testid="design-workorder-batch-bar"]')
      .find("button:not(:disabled)")
      .trigger("click");

    expect(wrapper.find('[data-testid="design-workorder-batch-bar"]').exists()).toBe(false);
  });

  it("导入与导出弹窗只维护本地展示状态", async () => {
    const wrapper = mountWorkOrder();

    await wrapper.get('[data-testid="design-workorder-import"]').trigger("click");

    expect(wrapper.get('[data-testid="design-workorder-import-overlay"]').text()).toContain(
      "本预览不会写入数据",
    );
    expect(wrapper.find('input[type="file"]').exists()).toBe(false);

    await wrapper.get('[data-testid="design-workorder-import-confirm"]').trigger("click");
    expect(wrapper.find('[data-testid="design-workorder-import-overlay"]').exists()).toBe(false);

    await wrapper.get('[data-testid="design-workorder-export-all"]').trigger("click");

    expect(wrapper.get('[data-testid="design-workorder-export-overlay"]').text()).toContain(
      "不会生成或下载文件",
    );

    window.dispatchEvent(new KeyboardEvent("keydown", { key: "Escape" }));
    await wrapper.vm.$nextTick();
    expect(wrapper.find('[data-testid="design-workorder-export-overlay"]').exists()).toBe(false);

    await wrapper.get('[data-testid="design-workorder-export-all"]').trigger("click");
    await wrapper.get('[data-testid="design-workorder-export-confirm"]').trigger("click");
    expect(wrapper.find('[data-testid="design-workorder-export-overlay"]').exists()).toBe(false);
  });

  it("编辑抽屉展示静态附件且关闭后不持久化", async () => {
    const wrapper = mountWorkOrder();

    await wrapper.get('[data-testid="design-workorder-edit-1"]').trigger("click");

    expect(wrapper.get('[data-testid="design-workorder-edit-overlay"]').text()).toContain(
      "香山东门_网幕近景_01.jpg",
    );
    expect(wrapper.find('input[type="file"]').exists()).toBe(false);

    const nameInput = wrapper
      .get('[data-testid="design-workorder-edit-overlay"]')
      .find('input:not([type="date"]):not([type="number"])');
    await nameInput.setValue("本地临时名称");
    await wrapper.get('[data-testid="design-workorder-edit-save"]').trigger("click");

    expect(wrapper.find('[data-testid="design-workorder-edit-overlay"]').exists()).toBe(false);

    await wrapper.get('[data-testid="design-workorder-edit-1"]').trigger("click");
    expect(
      wrapper
        .get('[data-testid="design-workorder-edit-overlay"]')
        .find('input:not([type="date"]):not([type="number"])').element.value,
    ).toBe("海淀区美国白蛾调查");
  });

  it("预览交互不会请求真实接口", async () => {
    const fetchMock = vi.fn();
    vi.stubGlobal("fetch", fetchMock);
    const wrapper = mountWorkOrder();

    await wrapper.get('[data-testid="design-workorder-search"]').setValue("美国白蛾");
    await wrapper.get('[data-testid="design-workorder-status-pending"]').trigger("click");
    await wrapper.get('[data-testid="design-workorder-select-all"]').trigger("click");
    await wrapper.get('[data-testid="design-workorder-export-selected"]').trigger("click");
    await wrapper.get('[data-testid="design-workorder-export-confirm"]').trigger("click");
    await wrapper.get('[data-testid="design-workorder-import"]').trigger("click");
    await wrapper.get('[data-testid="design-workorder-import-confirm"]').trigger("click");

    expect(fetchMock).not.toHaveBeenCalled();
  });
});
