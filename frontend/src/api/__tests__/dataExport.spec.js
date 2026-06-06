import { beforeEach, describe, expect, it, vi } from "vitest";

const httpMocks = vi.hoisted(() => ({
  apiFetch: vi.fn(),
  ensureApiSuccess: vi.fn(),
}));

vi.mock("../http.js", () => ({
  apiFetch: httpMocks.apiFetch,
  ensureApiSuccess: httpMocks.ensureApiSuccess,
}));

describe("api/dataExport", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    httpMocks.apiFetch.mockResolvedValue({
      blob: vi.fn().mockResolvedValue(new Blob(["xlsx"])),
      headers: new Headers({
        "content-disposition":
          "attachment; filename*=UTF-8''%E8%B0%83%E6%9F%A5%E6%95%B0%E6%8D%AE.xlsx",
      }),
      json: vi.fn().mockResolvedValue([]),
    });
    httpMocks.ensureApiSuccess.mockResolvedValue();
  });

  it("读取数据导出表列表", async () => {
    const { listDataExportTables } = await import("../dataExport.js");

    await listDataExportTables();

    expect(httpMocks.apiFetch).toHaveBeenCalledWith("/api/data-export/tables");
  });

  it("导出全部表时读取文件名", async () => {
    const { downloadAllDataExportTables } = await import("../dataExport.js");

    const result = await downloadAllDataExportTables();

    expect(httpMocks.apiFetch).toHaveBeenCalledWith("/api/data-export/download");
    expect(result.filename).toBe("调查数据.xlsx");
  });

  it("导出单表时编码中文表名", async () => {
    const { downloadDataExportTable } = await import("../dataExport.js");

    await downloadDataExportTable({
      schemaName: "survey",
      tableName: "春尺蠖幼虫调查表",
    });

    expect(httpMocks.apiFetch).toHaveBeenCalledWith(
      "/api/data-export/tables/survey/%E6%98%A5%E5%B0%BA%E8%A0%96%E5%B9%BC%E8%99%AB%E8%B0%83%E6%9F%A5%E8%A1%A8/download",
    );
  });
});
