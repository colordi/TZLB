import { flushPromises, mount } from "@vue/test-utils";
import { beforeEach, describe, expect, it, vi } from "vitest";

import DataExportView from "../DataExportView.vue";

const apiMocks = vi.hoisted(() => ({
  listPestExportTypes: vi.fn(),
  getPestExportMeta: vi.fn(),
  downloadPestTypeExport: vi.fn(),
  downloadBlob: vi.fn(),
  success: vi.fn(),
  error: vi.fn(),
}));

vi.mock("../../api/dataExport.js", () => ({
  listPestExportTypes: apiMocks.listPestExportTypes,
  getPestExportMeta: apiMocks.getPestExportMeta,
  downloadPestTypeExport: apiMocks.downloadPestTypeExport,
}));

vi.mock("../../utils/download.js", () => ({
  downloadBlob: apiMocks.downloadBlob,
}));

vi.mock("../../composables/useToast.js", () => ({
  useToast: () => ({
    success: apiMocks.success,
    error: apiMocks.error,
  }),
}));

function buildPestTypes() {
  return [
    {
      pest_type: "美国白蛾",
      total_row_count: 115,
      available_years: ["2025", "2026"],
      available_generations: ["第一代", "第二代"],
      tables: [
        { schema_name: "survey", table_name: "美国白蛾调查表", object_type: "table", column_count: 15, row_count: 50 },
        { schema_name: "ledger", table_name: "美国白蛾问题点位事件流水表", object_type: "table", column_count: 12, row_count: 40 },
        { schema_name: "ledger", table_name: "美国白蛾问题点位台账", object_type: "view", column_count: 10, row_count: 25 },
      ],
    },
    {
      pest_type: "春尺蠖",
      total_row_count: 65,
      available_years: ["2026"],
      available_generations: [],
      tables: [
        { schema_name: "survey", table_name: "春尺蠖成虫调查表", object_type: "table", column_count: 8, row_count: 10 },
        { schema_name: "survey", table_name: "春尺蠖幼虫调查表", object_type: "table", column_count: 12, row_count: 30 },
        { schema_name: "survey", table_name: "春尺蠖围环调查表", object_type: "table", column_count: 6, row_count: 5 },
      ],
    },
  ];
}

function mountView() {
  return mount(DataExportView);
}

describe("DataExportView", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    apiMocks.listPestExportTypes.mockResolvedValue(buildPestTypes());
    apiMocks.getPestExportMeta.mockImplementation((pestType) =>
      Promise.resolve(buildPestTypes().find((p) => p.pest_type === pestType)),
    );
    apiMocks.downloadPestTypeExport.mockResolvedValue({
      blob: new Blob(["pest"]),
      filename: "美国白蛾_20260705_120000.xlsx",
    });
    apiMocks.downloadBlob.mockResolvedValue({ delivery: "download" });
  });

  it("加载后默认展示第一个虫种，可通过选项卡切换", async () => {
    const wrapper = mountView();
    await flushPromises();

    expect(apiMocks.listPestExportTypes).toHaveBeenCalledTimes(1);
    expect(wrapper.text()).toContain("美国白蛾");
    expect(wrapper.text()).toContain("美国白蛾调查表");
    expect(wrapper.text()).toContain("115");

    // 默认未选中春尺蠖，表格内容不应出现
    expect(wrapper.find('[data-testid="pest-panel-春尺蠖"]').exists()).toBe(false);

    // 点击春尺蠖选项卡
    await wrapper.get('[data-testid="data-export-pest-春尺蠖"]').trigger("click");
    await flushPromises();

    expect(wrapper.find('[data-testid="pest-panel-春尺蠖"]').exists()).toBe(true);
    expect(wrapper.text()).toContain("春尺蠖成虫调查表");
    expect(wrapper.text()).toContain("65");
  });

  it("按虫种展示年份/世代筛选", async () => {
    const wrapper = mountView();
    await flushPromises();

    // 美国白蛾有年份和世代筛选
    const usMothPanel = wrapper.find('[data-testid="pest-panel-美国白蛾"]');
    expect(usMothPanel.text()).toContain("2025");
    expect(usMothPanel.text()).toContain("2026");
    expect(usMothPanel.text()).toContain("第一代");

    // 切换到春尺蠖，只有年份筛选
    await wrapper.get('[data-testid="data-export-pest-春尺蠖"]').trigger("click");
    await flushPromises();

    const chunPanel = wrapper.find('[data-testid="pest-panel-春尺蠖"]');
    expect(chunPanel.text()).toContain("2026");
    expect(chunPanel.findAll("select").length).toBe(1);
  });

  it("支持按年份世代筛选后导出", async () => {
    const wrapper = mountView();
    await flushPromises();

    // 选择年份和世代
    const panel = wrapper.find('[data-testid="pest-panel-美国白蛾"]');
    const yearSelect = panel.findAll("select")[0];
    yearSelect.setValue("2026");
    const genSelect = panel.findAll("select")[1];
    genSelect.setValue("第一代");
    await flushPromises();

    await wrapper.get('[data-testid="pest-download-美国白蛾"]').trigger("click");
    await flushPromises();

    expect(apiMocks.downloadPestTypeExport).toHaveBeenCalledWith("美国白蛾", {
      year: "2026",
      generation: "第一代",
    });
    expect(apiMocks.downloadBlob).toHaveBeenCalledWith(
      expect.any(Blob),
      "美国白蛾_20260705_120000.xlsx",
    );
    expect(apiMocks.success).toHaveBeenCalledWith("美国白蛾（2026年 第一代）已开始下载。", "导出成功");
  });

  it("按年份筛选后按钮文案显示筛选条件", async () => {
    const wrapper = mountView();
    await flushPromises();

    const panel = wrapper.find('[data-testid="pest-panel-美国白蛾"]');
    const yearSelect = panel.findAll("select")[0];
    yearSelect.setValue("2026");
    await flushPromises();

    const button = wrapper.get('[data-testid="pest-download-美国白蛾"]');
    expect(button.text()).toContain("2026年");
  });

  it("切换虫种时，若当前筛选值对新虫种不可用则自动清空", async () => {
    const wrapper = mountView();
    await flushPromises();

    const panel = wrapper.find('[data-testid="pest-panel-美国白蛾"]');
    const yearSelect = panel.findAll("select")[0];
    await yearSelect.setValue("2025");
    await flushPromises();

    await wrapper.get('[data-testid="data-export-pest-春尺蠖"]').trigger("click");
    await flushPromises();

    const chunPanel = wrapper.find('[data-testid="pest-panel-春尺蠖"]');
    expect(chunPanel.findAll("select")[0].element.value).toBe("");
  });

  it("选择筛选条件后请求带条件的元数据并更新记录数", async () => {
    apiMocks.getPestExportMeta.mockImplementation((pestType, filters) => {
      const base = buildPestTypes().find((p) => p.pest_type === pestType);
      return Promise.resolve({
        ...base,
        total_row_count: filters.year === "2026" ? 100 : base.total_row_count,
        tables: base.tables.map((t) => ({ ...t, row_count: filters.year === "2026" ? 10 : t.row_count })),
      });
    });

    const wrapper = mountView();
    await flushPromises();

    const panel = wrapper.find('[data-testid="pest-panel-美国白蛾"]');
    expect(wrapper.text()).toContain("115");

    const yearSelect = panel.findAll("select")[0];
    await yearSelect.setValue("2026");
    await flushPromises();

    expect(apiMocks.getPestExportMeta).toHaveBeenCalledWith("美国白蛾", {
      year: "2026",
      generation: undefined,
    });
    expect(wrapper.text()).toContain("100");
    expect(wrapper.text()).toContain("10");
  });

  it("读取列表失败时展示错误提示", async () => {
    apiMocks.listPestExportTypes.mockRejectedValueOnce(new Error("连接失败"));

    mountView();
    await flushPromises();

    expect(apiMocks.error).toHaveBeenCalledWith("连接失败", "读取虫种信息失败");
  });
});
