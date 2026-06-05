import { mount } from "@vue/test-utils";
import { describe, expect, it } from "vitest";

import RecordTable from "../RecordTable.vue";
import { createEmptyRecord } from "../fieldConfig.js";

function buildRecord(overrides = {}) {
  return {
    ...createEmptyRecord("春尺蠖"),
    town_or_street: "城东镇",
    location_id: "CC-001",
    location_name: "城东林场A区",
    description: "虫情记录",
    ...overrides,
  };
}

describe("RecordTable", () => {
  it("春尺蠖表格只渲染模板所需列", () => {
    const wrapper = mount(RecordTable, {
      props: {
        records: [buildRecord({ note: "现场北侧" })],
        pestType: "春尺蠖",
      },
    });

    const headers = wrapper.findAll("thead th").map((cell) => cell.text().replace(/\s+/g, ""));

    expect(headers).toEqual([
      "",
      "序号",
      "调查日期",
      "属地",
      "编号",
      "点位名称",
    ]);
    expect(wrapper.text()).not.toContain("发生位置");
    expect(wrapper.text()).not.toContain("总虫口数");
    expect(wrapper.text()).not.toContain("受害程度");
    expect(wrapper.text()).not.toContain("上报时间");
    expect(wrapper.text()).not.toContain("详细情况描述");
  });

  it("点击行会抛出 row-click 事件", async () => {
    const wrapper = mount(RecordTable, {
      props: {
        records: [buildRecord()],
        pestType: "春尺蠖",
      },
    });

    await wrapper.get("tbody tr").trigger("click");

    const events = wrapper.emitted("row-click");
    expect(events).toBeTruthy();
    expect(events[0]).toEqual([0]);
  });

  it("其他害虫列表仍保持同款 4 列紧凑总览", () => {
    const wrapper = mount(RecordTable, {
      props: {
        records: [
          {
            ...createEmptyRecord("其他害虫"),
            survey_date: "2026-04-17",
            town_or_street: "潞城镇",
            location_id: "QT0001",
            location_name: "畅和东路北京学校西侧",
            pest_name: "蚜虫",
            host_plant: "栾树",
            plot_type: "道路绿化",
            description: "描述",
          },
        ],
        pestType: "其他害虫",
      },
    });

    const headers = wrapper.findAll("thead th").map((cell) => cell.text().replace(/\s+/g, ""));
    expect(headers).toEqual(["", "序号", "调查日期", "属地", "编号", "点位名称"]);
    expect(wrapper.text()).not.toContain("虫害类型");
    expect(wrapper.text()).not.toContain("寄主树种");
  });

  it("空状态提示先导入调查数据", () => {
    const wrapper = mount(RecordTable, {
      props: {
        records: [],
        pestType: "春尺蠖",
      },
    });

    expect(wrapper.text()).toContain("请点击“导入调查数据”选取记录导入工作单。");
  });
});
