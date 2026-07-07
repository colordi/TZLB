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

function buildPayload(rowCount = 2) {
  const rows = [];
  for (let index = 0; index < rowCount; index += 1) {
    const day = String(rowCount - index).padStart(2, "0");
    rows.push({
      date: `2026-06-${day}`,
      daily_treatment_plants: 100 + index,
      cumulative_completed_points: 50 + index,
      daily_dispatch_points: index,
    });
  }
  return {
    columns: [
      { key: "date", label: "日期", type: "date" },
      { key: "daily_treatment_plants", label: "当日除治量（株）", type: "number" },
      { key: "cumulative_completed_points", label: "累积防治完成点数", type: "number" },
      { key: "daily_dispatch_points", label: "当日派单数", type: "number" },
    ],
    rows,
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

  it("加载美国白蛾每日统计并展示表格", async () => {
    const wrapper = mountView();
    await flushPromises();

    expect(apiMocks.getWhiteMothDailyStatistics).toHaveBeenCalledTimes(1);
    expect(wrapper.text()).toContain("美国白蛾每日信息统计");
    expect(wrapper.text()).toContain("2026-06-02");
    expect(wrapper.text()).toContain("2026-06-01");
    expect(wrapper.text()).toContain("当日除治量（株）");
    expect(wrapper.get('[data-testid="data-statistics-row-2026-06-01"]').text()).toContain(
      "101",
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
    expect(wrapper.findAll('[data-testid^="data-statistics-row-"]').length).toBe(0);
    expect(wrapper.find('[data-testid="data-statistics-next-page"]').exists()).toBe(false);
  });

  it("读取失败时展示错误提示", async () => {
    apiMocks.getWhiteMothDailyStatistics.mockRejectedValueOnce(new Error("连接失败"));

    mountView();
    await flushPromises();

    expect(apiMocks.error).toHaveBeenCalledWith("连接失败", "读取数据统计失败");
  });

  it("超过 7 行时只显示第一页，并可通过翻页查看后续行", async () => {
    apiMocks.getWhiteMothDailyStatistics.mockResolvedValueOnce(buildPayload(9));

    const wrapper = mountView();
    await flushPromises();

    expect(wrapper.findAll('[data-testid^="data-statistics-row-"]').length).toBe(7);
    expect(wrapper.text()).toContain("第 1 / 2 页");
    expect(wrapper.find('[data-testid="data-statistics-prev-page"]').attributes("disabled")).toBeDefined();

    await wrapper.get('[data-testid="data-statistics-next-page"]').trigger("click");
    await flushPromises();

    expect(wrapper.findAll('[data-testid^="data-statistics-row-"]').length).toBe(2);
    expect(wrapper.text()).toContain("第 2 / 2 页");
    expect(wrapper.find('[data-testid="data-statistics-next-page"]').attributes("disabled")).toBeDefined();

    await wrapper.get('[data-testid="data-statistics-prev-page"]').trigger("click");
    await flushPromises();

    expect(wrapper.text()).toContain("第 1 / 2 页");
  });
});
