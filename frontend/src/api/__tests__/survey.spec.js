import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { downloadImportTemplate, fetchPestTypes, fetchSurveyCandidates, uploadSurveyExcel } from "../survey.js";

function buildResponse(payload, ok = true) {
  return {
    ok,
    async json() {
      return payload;
    },
  };
}

function buildBlobResponse(blob, ok = true, contentDisposition = "") {
  return {
    ok,
    headers: {
      get(name) {
        if (name === "content-disposition") {
          return contentDisposition;
        }
        return null;
      },
    },
    async blob() {
      return blob;
    },
  };
}

describe("survey api", () => {
  beforeEach(() => {
    vi.stubGlobal("fetch", vi.fn());
  });

  afterEach(() => {
    vi.unstubAllGlobals();
    vi.restoreAllMocks();
  });

  it("fetchSurveyCandidates 保持原有候选记录查询参数", async () => {
    global.fetch.mockResolvedValue(buildResponse([]));

    await fetchSurveyCandidates({
      date: "2026-04-01",
      pestType: "春尺蠖",
    });

    expect(global.fetch).toHaveBeenCalledWith(
      "/api/survey/candidates?date=2026-04-01&pest_type=%E6%98%A5%E5%B0%BA%E8%A0%96",
      expect.objectContaining({
        credentials: "same-origin",
      }),
    );
  });

  it("uploadSurveyExcel 使用 multipart 表单并携带 dry_run 参数", async () => {
    global.fetch.mockResolvedValue(buildResponse({ ok: true }));
    const file = new File(["xlsx"], "调查.xlsx", {
      type: "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    });

    await uploadSurveyExcel({
      file,
      dryRun: false,
    });

    const [, init] = global.fetch.mock.calls[0];
    expect(global.fetch.mock.calls[0][0]).toBe("/api/survey/excel-import?dry_run=false");
    expect(init).toEqual(
      expect.objectContaining({
        method: "POST",
        credentials: "same-origin",
      }),
    );
    expect(init.body).toBeInstanceOf(FormData);
    expect(init.body.get("file")).toBe(file);
  });

  it("fetchPestTypes 请求虫种列表接口", async () => {
    const payload = [
      { key: "美国白蛾", label: "美国白蛾" },
      { key: "杨树食叶害虫", label: "杨树食叶害虫" },
    ];
    global.fetch.mockResolvedValue(buildResponse(payload));

    const result = await fetchPestTypes();

    expect(global.fetch).toHaveBeenCalledWith(
      "/api/survey/pest-types",
      expect.objectContaining({
        credentials: "same-origin",
      }),
    );
    expect(result).toEqual(payload);
  });

  it("downloadImportTemplate 返回 blob 和解码后的文件名", async () => {
    const blob = new Blob(["xlsx-template"]);
    global.fetch.mockResolvedValue(
      buildBlobResponse(
        blob,
        true,
        "attachment; filename*=UTF-8''%E6%A8%A1%E6%9D%BF.xlsx",
      ),
    );

    const result = await downloadImportTemplate("美国白蛾");

    expect(global.fetch).toHaveBeenCalledWith(
      `/api/survey/import-template?pest_type=${encodeURIComponent("美国白蛾")}`,
      expect.objectContaining({
        credentials: "same-origin",
      }),
    );
    expect(result.blob).toBe(blob);
    expect(result.filename).toBe("模板.xlsx");
  });
});
