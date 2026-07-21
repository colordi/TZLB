import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import {
  deletePointDateImage,
  fetchPointDateImages,
  generateWorkorderBatch,
  getWorkorderBatchJobStatus,
  startWorkorderBatchJob,
  uploadPointDateImages,
} from "../workorder.js";

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

describe("workorder api", () => {
  beforeEach(() => {
    vi.stubGlobal("fetch", vi.fn());
  });

  afterEach(() => {
    vi.unstubAllGlobals();
    vi.restoreAllMocks();
  });

  it("fetchPointDateImages 按日期与点位编号查询图片列表", async () => {
    global.fetch.mockResolvedValue(buildResponse({ images: [] }));

    await fetchPointDateImages({ surveyDate: "2026-05-26", pointCode: "MQ001" });

    expect(global.fetch.mock.calls[0][0]).toBe(
      "/api/workorder/point-date-images?survey_date=2026-05-26&point_code=MQ001",
    );
  });

  it("fetchPointDateImages 不传点位编号时查询当日全部图片", async () => {
    global.fetch.mockResolvedValue(buildResponse({ images: [] }));

    await fetchPointDateImages({ surveyDate: "2026-05-26" });

    expect(global.fetch.mock.calls[0][0]).toBe(
      "/api/workorder/point-date-images?survey_date=2026-05-26",
    );
  });

  it("uploadPointDateImages 使用 multipart 表单上传点位图片", async () => {
    global.fetch.mockResolvedValue(buildResponse({ saved_count: 1 }));
    const file = new File(["image"], "现场.jpg", { type: "image/jpeg" });

    await uploadPointDateImages({
      surveyDate: "2026-05-26",
      pointCode: "MQ001",
      files: [file],
    });

    const [, init] = global.fetch.mock.calls[0];
    expect(global.fetch.mock.calls[0][0]).toBe("/api/workorder/point-date-images");
    expect(init.method).toBe("POST");
    expect(init.body).toBeInstanceOf(FormData);
    expect(init.body.get("survey_date")).toBe("2026-05-26");
    expect(init.body.get("point_code")).toBe("MQ001");
    expect(init.body.get("files")).toBe(file);
  });

  it("deletePointDateImage 调用 DELETE 并携带点位编号", async () => {
    global.fetch.mockResolvedValue(buildResponse({ deleted: "MQ001-1.jpg" }));

    await deletePointDateImage({
      surveyDate: "2026-05-26",
      pointCode: "MQ001",
      fileName: "MQ001-1.jpg",
    });

    const [url, init] = global.fetch.mock.calls[0];
    expect(url).toBe("/api/workorder/point-date-images/2026-05-26/MQ001-1.jpg?point_code=MQ001");
    expect(init.method).toBe("DELETE");
  });

  it("generateWorkorderBatch 向批量导出接口 POST JSON 并返回 blob", async () => {
    const blob = new Blob(["zip-content"]);
    global.fetch.mockResolvedValue(
      buildBlobResponse(
        blob,
        true,
        "attachment; filename*=UTF-8''%E6%89%B9%E9%87%8F%E5%AF%BC%E5%87%BA.zip",
      ),
    );

    const payload = {
      pest_type: "春尺蠖",
      task_type: "春尺蠖防治",
      task: "2026春尺蠖防治",
      records: [{ survey_date: "2026-04-01", location_name: "神仙村" }],
    };
    const result = await generateWorkorderBatch(payload);

    const [, init] = global.fetch.mock.calls[0];
    expect(global.fetch.mock.calls[0][0]).toBe("/api/workorder/generate-batch");
    expect(init).toEqual(
      expect.objectContaining({
        method: "POST",
        credentials: "same-origin",
        body: JSON.stringify(payload),
      }),
    );
    expect(result.blob).toBe(blob);
    expect(result.filename).toBe("批量导出.zip");
  });

  it("startWorkorderBatchJob 创建批量任务并返回 job_id", async () => {
    global.fetch.mockResolvedValue(
      buildResponse({ job_id: "abc", total: 3, status: "queued" }),
    );

    const payload = {
      pest_type: "春尺蠖",
      task_type: "春尺蠖防治",
      task: "2026春尺蠖防治",
      records: [{ survey_date: "2026-04-01", location_name: "神仙村" }],
    };
    const result = await startWorkorderBatchJob(payload);

    expect(global.fetch.mock.calls[0][0]).toBe("/api/workorder/generate-batch-jobs");
    expect(result).toEqual({ job_id: "abc", total: 3, status: "queued" });
  });

  it("getWorkorderBatchJobStatus 查询任务进度", async () => {
    global.fetch.mockResolvedValue(
      buildResponse({
        job_id: "abc",
        status: "running",
        current: 1,
        total: 3,
        percent: 33,
        phase: "generating",
        message: "正在生成 1/2",
      }),
    );

    const result = await getWorkorderBatchJobStatus("abc");

    expect(global.fetch.mock.calls[0][0]).toBe("/api/workorder/generate-batch-jobs/abc");
    expect(result.percent).toBe(33);
    expect(result.status).toBe("running");
  });
});
