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
          "attachment; filename*=UTF-8''%E7%BE%8E%E5%9B%BD%E7%99%BD%E8%9B%BE_20260705.xlsx",
      }),
      json: vi.fn().mockResolvedValue([]),
    });
    httpMocks.ensureApiSuccess.mockResolvedValue();
  });

  it("读取虫种导出列表", async () => {
    const { listPestExportTypes } = await import("../dataExport.js");

    await listPestExportTypes();

    expect(httpMocks.apiFetch).toHaveBeenCalledWith("/api/data-export/pest-types");
  });

  it("导出虫种时读取文件名", async () => {
    const { downloadPestTypeExport } = await import("../dataExport.js");

    const result = await downloadPestTypeExport("美国白蛾");

    expect(httpMocks.apiFetch).toHaveBeenCalledWith(
      "/api/data-export/pest/%E7%BE%8E%E5%9B%BD%E7%99%BD%E8%9B%BE/download",
    );
    expect(result.filename).toBe("美国白蛾_20260705.xlsx");
  });

  it("导出虫种时传递年份和世代参数", async () => {
    const { downloadPestTypeExport } = await import("../dataExport.js");

    await downloadPestTypeExport("美国白蛾", { year: "2026", generation: "1" });

    expect(httpMocks.apiFetch).toHaveBeenCalledWith(
      "/api/data-export/pest/%E7%BE%8E%E5%9B%BD%E7%99%BD%E8%9B%BE/download?year=2026&generation=1",
    );
  });
});
