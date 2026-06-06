import { flushPromises, mount } from "@vue/test-utils";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import ExcelImportDialog from "../ExcelImportDialog.vue";

const apiMocks = vi.hoisted(() => ({
  uploadSurveyExcel: vi.fn(),
  success: vi.fn(),
  error: vi.fn(),
  info: vi.fn(),
}));

vi.mock("../../../api/survey.js", () => ({
  uploadSurveyExcel: apiMocks.uploadSurveyExcel,
}));

vi.mock("../../../composables/useToast.js", () => ({
  useToast: () => ({
    success: apiMocks.success,
    error: apiMocks.error,
    info: apiMocks.info,
  }),
}));

function buildPreview(overrides = {}) {
  return {
    file_name: "调查.xlsx",
    dry_run: true,
    totals: {
      sheet_count: 1,
      row_count: 2,
      valid_rows: 2,
      inserted_rows: 0,
      skipped_duplicate_rows: 1,
      error_count: 0,
      ...overrides.totals,
    },
    sheets: [
      {
        sheet_name: "春尺蠖幼虫调查表",
        schema_name: "survey",
        table_name: "春尺蠖幼虫调查表",
        row_count: 2,
        valid_rows: 2,
        inserted_rows: 0,
        skipped_duplicate_rows: 1,
        warnings: ["第 2 行已存在，已跳过"],
        errors: [],
        ...overrides.sheet,
      },
    ],
  };
}

function mountDialog() {
  return mount(ExcelImportDialog, {
    props: {
      open: true,
    },
    global: {
      stubs: {
        teleport: true,
      },
    },
  });
}

async function chooseFile(wrapper) {
  const file = new File(["xlsx"], "调查.xlsx", {
    type: "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
  });
  const input = wrapper.get('[data-testid="survey-excel-file"]');
  Object.defineProperty(input.element, "files", {
    value: [file],
    configurable: true,
  });
  await input.trigger("change");
  return file;
}

describe("ExcelImportDialog", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("选择文件后先执行 dry-run 预览并展示汇总", async () => {
    apiMocks.uploadSurveyExcel.mockResolvedValueOnce(buildPreview());
    const wrapper = mountDialog();
    const file = await chooseFile(wrapper);

    await wrapper.get('[data-testid="survey-excel-preview"]').trigger("click");
    await flushPromises();

    expect(apiMocks.uploadSurveyExcel).toHaveBeenCalledWith({
      file,
      dryRun: true,
    });
    expect(wrapper.text()).toContain("sheet 1");
    expect(wrapper.text()).toContain("可导入 1");
    expect(wrapper.text()).toContain("survey.春尺蠖幼虫调查表");
    expect(wrapper.text()).toContain("第 2 行已存在，已跳过");
    expect(apiMocks.success).toHaveBeenCalledWith("校验通过，可导入 1 条记录。", "预览完成");
  });

  it("预览结果展示 ledger 目标表", async () => {
    apiMocks.uploadSurveyExcel.mockResolvedValueOnce(
      buildPreview({
        sheet: {
          sheet_name: "2026年其他害虫问题点位事件流水表",
          schema_name: "ledger",
          table_name: "2026年其他害虫问题点位事件流水表",
        },
      }),
    );
    const wrapper = mountDialog();
    await chooseFile(wrapper);

    await wrapper.get('[data-testid="survey-excel-preview"]').trigger("click");
    await flushPromises();

    expect(wrapper.text()).toContain("ledger.2026年其他害虫问题点位事件流水表");
  });

  it("预览无错误时确认入库会再次提交 dry_run=false", async () => {
    apiMocks.uploadSurveyExcel
      .mockResolvedValueOnce(buildPreview())
      .mockResolvedValueOnce(
        buildPreview({
          totals: {
            inserted_rows: 1,
            skipped_duplicate_rows: 1,
          },
          sheet: {
            inserted_rows: 1,
          },
        }),
      );
    const wrapper = mountDialog();
    const file = await chooseFile(wrapper);

    await wrapper.get('[data-testid="survey-excel-preview"]').trigger("click");
    await flushPromises();
    await wrapper.get('[data-testid="survey-excel-confirm"]').trigger("click");
    await flushPromises();

    expect(apiMocks.uploadSurveyExcel).toHaveBeenLastCalledWith({
      file,
      dryRun: false,
    });
    expect(apiMocks.success).toHaveBeenCalledWith("已导入 1 条记录。", "导入完成");
    expect(wrapper.emitted("imported")).toBeTruthy();
  });

  it("预览存在错误时展示错误并禁用确认入库", async () => {
    apiMocks.uploadSurveyExcel.mockResolvedValueOnce(
      buildPreview({
        totals: {
          valid_rows: 0,
          skipped_duplicate_rows: 0,
          error_count: 1,
        },
        sheet: {
          valid_rows: 0,
          skipped_duplicate_rows: 0,
          errors: ["缺少必填列：调查日期"],
        },
      }),
    );
    const wrapper = mountDialog();
    await chooseFile(wrapper);

    await wrapper.get('[data-testid="survey-excel-preview"]').trigger("click");
    await flushPromises();

    expect(wrapper.text()).toContain("缺少必填列：调查日期");
    expect(wrapper.get('[data-testid="survey-excel-confirm"]').attributes("disabled"))
      .toBeDefined();
    expect(apiMocks.error).toHaveBeenCalledWith("Excel 存在校验错误，暂未入库。", "预览失败");
  });
});
