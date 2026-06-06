import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { fetchSurveyCandidates, uploadSurveyExcel } from "../survey.js";

function buildResponse(payload, ok = true) {
  return {
    ok,
    async json() {
      return payload;
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
});
