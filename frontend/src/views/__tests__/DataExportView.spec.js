import { flushPromises, mount } from "@vue/test-utils";
import { beforeEach, describe, expect, it, vi } from "vitest";

import DataExportView from "../DataExportView.vue";

const apiMocks = vi.hoisted(() => ({
  listDataExportTables: vi.fn(),
  downloadAllDataExportTables: vi.fn(),
  downloadDataExportTable: vi.fn(),
  downloadBlob: vi.fn(),
  success: vi.fn(),
  error: vi.fn(),
}));

vi.mock("../../api/dataExport.js", () => ({
  listDataExportTables: apiMocks.listDataExportTables,
  downloadAllDataExportTables: apiMocks.downloadAllDataExportTables,
  downloadDataExportTable: apiMocks.downloadDataExportTable,
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

function buildTables() {
  return [
    {
      schema_name: "survey",
      table_name: "春尺蠖幼虫调查表",
      object_type: "table",
      column_count: 12,
      row_count: 30,
    },
    {
      schema_name: "ledger",
      table_name: "2026年美国白蛾第一代问题点位台账",
      object_type: "table",
      column_count: 8,
      row_count: 2,
    },
    {
      schema_name: "ledger",
      table_name: "2026年美国白蛾第一代问题点位视图",
      object_type: "view",
      column_count: 8,
      row_count: 2,
    },
  ];
}

function mountView() {
  return mount(DataExportView);
}

describe("DataExportView", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    apiMocks.listDataExportTables.mockResolvedValue(buildTables());
    apiMocks.downloadAllDataExportTables.mockResolvedValue({
      blob: new Blob(["all"]),
      filename: "调查数据导出.xlsx",
    });
    apiMocks.downloadDataExportTable.mockResolvedValue({
      blob: new Blob(["table"]),
      filename: "survey_春尺蠖幼虫调查表.xlsx",
    });
    apiMocks.downloadBlob.mockResolvedValue({ delivery: "download" });
  });

  it("加载并按 schema 展示表和视图", async () => {
    const wrapper = mountView();
    await flushPromises();

    expect(apiMocks.listDataExportTables).toHaveBeenCalledTimes(1);
    expect(wrapper.text()).toContain("survey 调查数据");
    expect(wrapper.text()).toContain("ledger 台账数据");
    expect(wrapper.text()).toContain("春尺蠖幼虫调查表");
    expect(wrapper.text()).toContain("2026年美国白蛾第一代问题点位台账");
    expect(wrapper.text()).toContain("2026年美国白蛾第一代问题点位视图");
    expect(wrapper.text()).toContain("视图");
    expect(wrapper.text()).toContain("34");
  });

  it("支持导出全部数据表", async () => {
    const wrapper = mountView();
    await flushPromises();

    await wrapper.get('[data-testid="data-export-download-all"]').trigger("click");
    await flushPromises();

    expect(apiMocks.downloadAllDataExportTables).toHaveBeenCalledTimes(1);
    expect(apiMocks.downloadBlob).toHaveBeenCalledWith(
      expect.any(Blob),
      "调查数据导出.xlsx",
    );
    expect(apiMocks.success).toHaveBeenCalledWith("全部表和视图已开始下载。", "导出成功");
  });

  it("支持导出单张表", async () => {
    const wrapper = mountView();
    await flushPromises();

    await wrapper
      .get('[data-testid="data-export-download-survey.春尺蠖幼虫调查表"]')
      .trigger("click");
    await flushPromises();

    expect(apiMocks.downloadDataExportTable).toHaveBeenCalledWith({
      schemaName: "survey",
      tableName: "春尺蠖幼虫调查表",
    });
    expect(apiMocks.downloadBlob).toHaveBeenCalledWith(
      expect.any(Blob),
      "survey_春尺蠖幼虫调查表.xlsx",
    );
  });

  it("读取列表失败时展示错误提示", async () => {
    apiMocks.listDataExportTables.mockRejectedValueOnce(new Error("连接失败"));

    mountView();
    await flushPromises();

    expect(apiMocks.error).toHaveBeenCalledWith("连接失败", "读取表和视图失败");
  });
});
