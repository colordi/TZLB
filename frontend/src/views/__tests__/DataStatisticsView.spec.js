import { flushPromises, mount } from "@vue/test-utils";
import { beforeEach, describe, expect, it, vi } from "vitest";

import DataStatisticsView from "../DataStatisticsView.vue";

const apiMocks = vi.hoisted(() => ({
  getWhiteMothDailyStatistics: vi.fn(),
  error: vi.fn(),
}));

vi.mock("../../api/statistics.js", () => ({
  getWhiteMothDailyStatistics: apiMocks.getWhiteMothDailyStatistics,
}));

vi.mock("../../composables/useToast.js", () => ({
  useToast: () => ({
    error: apiMocks.error,
  }),
}));

function buildPayload() {
  return {
    columns: [
      { key: "date", label: "日期", type: "date" },
      { key: "daily_treatment_plants", label: "当日除治量（株）", type: "number" },
      { key: "cumulative_completed_points", label: "累积防治完成点数", type: "number" },
      { key: "daily_dispatch_points", label: "当日派单数", type: "number" },
    ],
    rows: [
      {
        date: "2026-06-01",
        daily_treatment_plants: 210,
        cumulative_completed_points: 51,
        daily_dispatch_points: 28,
      },
      {
        date: "2026-05-31",
        daily_treatment_plants: 122,
        cumulative_completed_points: 37,
        daily_dispatch_points: 10,
      },
    ],
  };
}

function mountView() {
  return mount(DataStatisticsView);
}

describe("DataStatisticsView", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    apiMocks.getWhiteMothDailyStatistics.mockResolvedValue(buildPayload());
  });

  it("加载美国白蛾每日统计并展示最新日摘要和表格", async () => {
    const wrapper = mountView();
    await flushPromises();

    expect(apiMocks.getWhiteMothDailyStatistics).toHaveBeenCalledTimes(1);
    expect(wrapper.text()).toContain("美国白蛾每日信息统计");
    expect(wrapper.text()).toContain("2026-06-01");
    expect(wrapper.text()).toContain("210");
    expect(wrapper.text()).toContain("51");
    expect(wrapper.text()).toContain("当日除治量（株）");
    expect(wrapper.get('[data-testid="data-statistics-row-2026-05-31"]').text()).toContain(
      "122",
    );
  });

  it("其它虫种入口为占位不可点击", async () => {
    const wrapper = mountView();
    await flushPromises();

    expect(wrapper.get('[data-testid="data-statistics-pest-white-moth"]').attributes("disabled")).toBeUndefined();
    expect(wrapper.get('[data-testid="data-statistics-pest-poplar-inchworm"]').attributes("disabled")).toBeDefined();
    expect(wrapper.get('[data-testid="data-statistics-pest-sophora-inchworm"]').attributes("disabled")).toBeDefined();
    expect(wrapper.get('[data-testid="data-statistics-pest-other-pests"]').attributes("disabled")).toBeDefined();
  });

  it("没有统计数据时展示空状态", async () => {
    apiMocks.getWhiteMothDailyStatistics.mockResolvedValueOnce({
      columns: [{ key: "date", label: "日期", type: "date" }],
      rows: [],
    });

    const wrapper = mountView();
    await flushPromises();

    expect(wrapper.text()).toContain("暂无美国白蛾每日统计数据。");
    expect(wrapper.text()).toContain("--");
  });

  it("读取失败时展示错误提示", async () => {
    apiMocks.getWhiteMothDailyStatistics.mockRejectedValueOnce(new Error("连接失败"));

    mountView();
    await flushPromises();

    expect(apiMocks.error).toHaveBeenCalledWith("连接失败", "读取数据统计失败");
  });
});
